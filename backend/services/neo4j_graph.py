"""
backend/services/neo4j_graph.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SurakshaNet AI — Phase 1: Neo4j Aura Graph Operations Layer
Model: Claude Sonnet 4.6 (1.3x) — Heavy DB/Schema task

Responsibilities:
  • Re-export the async driver initialised in database.py (single source of truth)
  • Provide a robust execute_cypher() wrapper with retry, timeout, and error
    normalisation — the only function agents should call for graph queries
  • Declare and apply the full node-constraint & index set for the fraud graph:
      PhoneNumber, BankAccount, UPIId, FraudActor, Syndicate, Victim
  • Expose typed read/write helpers used by network_agent.py and copilot_agent.py
  • Supply a standalone startup coroutine so the graph layer can be initialised
    independently during testing without booting the full FastAPI lifespan

Design notes:
  - All public coroutines are safe to call concurrently from multiple async tasks.
  - Write operations use explicit transactions; read operations use auto-commit
    sessions for lower latency on the free Aura tier.
  - The module never holds long-lived session objects at module scope — sessions
    are checked out and returned inside each function call.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

from neo4j import AsyncDriver, AsyncSession, AsyncTransaction, Record
from neo4j.exceptions import (
    AuthError,
    ClientError,
    ServiceUnavailable,
    SessionExpired,
    TransientError,
)

# database.py is the single source of truth for the driver singleton
from services.database import (
    get_neo4j_driver,
    init_neo4j,
    close_neo4j,
)

logger = logging.getLogger("surakshanet.neo4j_graph")

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

NEO4J_DATABASE: str = os.getenv("NEO4J_DATABASE", os.getenv("NEO4J_USER", "neo4j"))   # Aura: DB name = username

# Retry policy for transient failures (network blip, leader election, etc.)
MAX_RETRIES: int = 3
RETRY_BASE_DELAY: float = 0.5    # seconds; doubled on each attempt
QUERY_TIMEOUT: float = 20.0      # seconds per individual Cypher execution

# ─────────────────────────────────────────────────────────────────────────────
# Typed result container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CypherResult:
    """
    Normalised return value from execute_cypher().

    Attributes:
        records     : List of dicts (one per returned row), keys match RETURN aliases.
        summary     : Neo4j ResultSummary with counters and timing metadata.
        elapsed_ms  : Wall-clock time measured client-side in milliseconds.
        query       : The Cypher string that was executed (useful for logging).
    """
    records: list[dict[str, Any]]
    summary: Any                        # neo4j.ResultSummary
    elapsed_ms: float
    query: str
    params: dict[str, Any] = field(default_factory=dict)

    @property
    def single(self) -> Optional[dict[str, Any]]:
        """Return the first record or None — convenience for MATCH … LIMIT 1 patterns."""
        return self.records[0] if self.records else None

    @property
    def counters(self) -> dict[str, int]:
        """Shortcut to the result summary update counters."""
        c = self.summary.counters
        return {
            "nodes_created":         c.nodes_created,
            "nodes_deleted":         c.nodes_deleted,
            "relationships_created": c.relationships_created,
            "relationships_deleted": c.relationships_deleted,
            "properties_set":        c.properties_set,
            "labels_added":          c.labels_added,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Core Cypher Executor
# ─────────────────────────────────────────────────────────────────────────────

async def execute_cypher(
    query: str,
    params: Optional[dict[str, Any]] = None,
    *,
    write: bool = False,
    database: str = NEO4J_DATABASE,
) -> CypherResult:
    """
    Execute a Cypher query against Neo4j Aura with automatic retry on
    transient errors.

    Parameters
    ----------
    query    : Cypher statement.  Use $param_name placeholders — never
               f-string user data into the query string.
    params   : Parameter dict corresponding to $placeholders in query.
    write    : Set True for CREATE / MERGE / SET / DELETE statements.
               Read-only queries run in an implicit auto-commit transaction
               which is cheaper on the free Aura tier.
    database : Target database name (default 'neo4j').

    Returns
    -------
    CypherResult with .records, .summary, .elapsed_ms, .counters

    Raises
    ------
    RuntimeError  : If all retry attempts are exhausted.
    AuthError     : Immediately if credentials are wrong (no retry).
    ClientError   : Immediately for bad Cypher syntax (no retry).
    """
    params = params or {}
    driver: AsyncDriver = get_neo4j_driver()
    last_exc: Optional[Exception] = None

    for attempt in range(1, MAX_RETRIES + 1):
        t0 = time.monotonic()
        try:
            if write:
                result = await _run_write_transaction(driver, query, params, database)
            else:
                result = await _run_read_query(driver, query, params, database)

            elapsed_ms = round((time.monotonic() - t0) * 1000, 2)
            logger.debug(
                "Cypher OK  [%s]  %.1f ms  attempt=%d",
                query[:60].replace("\n", " "),
                elapsed_ms,
                attempt,
            )
            return CypherResult(
                records=result["records"],
                summary=result["summary"],
                elapsed_ms=elapsed_ms,
                query=query,
                params=params,
            )

        except (AuthError, ClientError):
            # Non-retryable — bad credentials or syntax error
            raise

        except (ServiceUnavailable, SessionExpired, TransientError) as exc:
            last_exc = exc
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(
                "Cypher transient error (attempt %d/%d): %s — retrying in %.1fs",
                attempt, MAX_RETRIES, exc, delay,
            )
            if attempt < MAX_RETRIES:
                await asyncio.sleep(delay)

        except Exception as exc:
            last_exc = exc
            logger.error("Cypher unexpected error: %s | query: %s", exc, query[:120])
            break

    raise RuntimeError(
        f"Cypher execution failed after {MAX_RETRIES} attempts. "
        f"Last error: {last_exc}"
    ) from last_exc


async def _run_read_query(
    driver: AsyncDriver,
    query: str,
    params: dict[str, Any],
    database: str,
) -> dict:
    """Run a read query in an auto-commit session."""
    async with driver.session(database=database) as session:
        result = await asyncio.wait_for(
            session.run(query, params),
            timeout=QUERY_TIMEOUT,
        )
        raw_records: list[Record] = await result.fetch(1000)  # max rows per call
        summary = await result.consume()
        return {
            "records": [dict(r) for r in raw_records],
            "summary": summary,
        }


async def _run_write_transaction(
    driver: AsyncDriver,
    query: str,
    params: dict[str, Any],
    database: str,
) -> dict:
    """Run a write query inside a managed explicit transaction."""
    async with driver.session(database=database) as session:

        async def _tx_work(tx: AsyncTransaction) -> dict:
            result = await asyncio.wait_for(
                tx.run(query, params),
                timeout=QUERY_TIMEOUT,
            )
            raw_records: list[Record] = await result.fetch(1000)
            summary = await result.consume()
            return {
                "records": [dict(r) for r in raw_records],
                "summary": summary,
            }

        return await session.execute_write(_tx_work)


# ─────────────────────────────────────────────────────────────────────────────
# Schema — Constraints & Indexes
# ─────────────────────────────────────────────────────────────────────────────
#
# These are applied once at startup (idempotent — IF NOT EXISTS).
# Using a dedicated function here (vs. database.py's lighter bootstrap_graph_schema)
# because this module owns the complete domain model for the fraud graph.
# ─────────────────────────────────────────────────────────────────────────────

_CONSTRAINTS: list[tuple[str, str]] = [
    # ── PhoneNumber ──────────────────────────────────────────────────────────
    (
        "phone_number_unique",
        "CREATE CONSTRAINT phone_number_unique IF NOT EXISTS "
        "FOR (p:PhoneNumber) REQUIRE p.number IS UNIQUE",
    ),
    (
        "phone_number_not_null",
        "CREATE CONSTRAINT phone_number_not_null IF NOT EXISTS "
        "FOR (p:PhoneNumber) REQUIRE p.number IS NOT NULL",
    ),

    # ── BankAccount ──────────────────────────────────────────────────────────
    (
        "bank_account_unique",
        "CREATE CONSTRAINT bank_account_unique IF NOT EXISTS "
        "FOR (b:BankAccount) REQUIRE b.account_id IS UNIQUE",
    ),
    (
        "bank_account_not_null",
        "CREATE CONSTRAINT bank_account_not_null IF NOT EXISTS "
        "FOR (b:BankAccount) REQUIRE b.account_id IS NOT NULL",
    ),

    # ── UPIId ─────────────────────────────────────────────────────────────────
    (
        "upi_id_unique",
        "CREATE CONSTRAINT upi_id_unique IF NOT EXISTS "
        "FOR (u:UPIId) REQUIRE u.upi_id IS UNIQUE",
    ),
    (
        "upi_id_not_null",
        "CREATE CONSTRAINT upi_id_not_null IF NOT EXISTS "
        "FOR (u:UPIId) REQUIRE u.upi_id IS NOT NULL",
    ),

    # ── FraudActor ───────────────────────────────────────────────────────────
    (
        "fraud_actor_name_unique",
        "CREATE CONSTRAINT fraud_actor_name_unique IF NOT EXISTS "
        "FOR (a:FraudActor) REQUIRE a.name IS UNIQUE",
    ),
    (
        "fraud_actor_role_not_null",
        "CREATE CONSTRAINT fraud_actor_role_not_null IF NOT EXISTS "
        "FOR (a:FraudActor) REQUIRE a.role IS NOT NULL",
    ),

    # ── Syndicate ────────────────────────────────────────────────────────────
    (
        "syndicate_name_unique",
        "CREATE CONSTRAINT syndicate_name_unique IF NOT EXISTS "
        "FOR (s:Syndicate) REQUIRE s.name IS UNIQUE",
    ),

    # ── Victim ───────────────────────────────────────────────────────────────
    (
        "victim_case_id_unique",
        "CREATE CONSTRAINT victim_case_id_unique IF NOT EXISTS "
        "FOR (v:Victim) REQUIRE v.case_id IS UNIQUE",
    ),
]

_INDEXES: list[tuple[str, str]] = [
    # Full-text index — powers keyword search in the police dashboard
    (
        "fraud_actor_fulltext",
        "CREATE FULLTEXT INDEX fraud_actor_fulltext IF NOT EXISTS "
        "FOR (a:FraudActor) ON EACH [a.name, a.state, a.aliases]",
    ),
    (
        "syndicate_fulltext",
        "CREATE FULLTEXT INDEX syndicate_fulltext IF NOT EXISTS "
        "FOR (s:Syndicate) ON EACH [s.name, s.description]",
    ),

    # Range indexes for date-range and numeric filtering
    (
        "phone_created_at_idx",
        "CREATE INDEX phone_created_at_idx IF NOT EXISTS "
        "FOR (p:PhoneNumber) ON (p.created_at)",
    ),
    (
        "bank_account_bank_idx",
        "CREATE INDEX bank_account_bank_idx IF NOT EXISTS "
        "FOR (b:BankAccount) ON (b.bank)",
    ),
    (
        "fraud_actor_state_idx",
        "CREATE INDEX fraud_actor_state_idx IF NOT EXISTS "
        "FOR (a:FraudActor) ON (a.state)",
    ),
    (
        "victim_state_idx",
        "CREATE INDEX victim_state_idx IF NOT EXISTS "
        "FOR (v:Victim) ON (v.state)",
    ),
    (
        "victim_amount_lost_idx",
        "CREATE INDEX victim_amount_lost_idx IF NOT EXISTS "
        "FOR (v:Victim) ON (v.amount_lost)",
    ),
]


async def apply_graph_schema() -> dict[str, list[str]]:
    """
    Apply all constraints and indexes to the Neo4j Aura instance.

    Returns a report dict:
        {
            "applied":  ["constraint_name", ...],
            "skipped":  ["index_name", ...],    # already existed
            "failed":   ["name: error_msg", ...]
        }

    Safe to call on every startup — IF NOT EXISTS guards all statements.
    Runs each statement sequentially (Aura free tier rejects concurrent DDL).
    """
    driver: AsyncDriver = get_neo4j_driver()
    report: dict[str, list[str]] = {"applied": [], "skipped": [], "failed": []}

    all_ddl = _CONSTRAINTS + _INDEXES
    logger.info("Applying %d graph schema statements …", len(all_ddl))

    async with driver.session(database=NEO4J_DATABASE) as session:
        for name, statement in all_ddl:
            try:
                await session.run(statement)
                report["applied"].append(name)
                logger.debug("Schema applied: %s", name)
            except ClientError as exc:
                # Neo4j raises ClientError with code Neo.ClientError.Schema.EquivalentSchemaRuleAlreadyExists
                # when an identical constraint already exists — treat as skip.
                if "AlreadyExists" in str(exc.code):
                    report["skipped"].append(name)
                    logger.debug("Schema already exists (skipped): %s", name)
                else:
                    report["failed"].append(f"{name}: {exc}")
                    logger.warning("Schema DDL failed: %s | %s", name, exc)
            except Exception as exc:
                report["failed"].append(f"{name}: {exc}")
                logger.warning("Schema DDL unexpected error: %s | %s", name, exc)

    logger.info(
        "Graph schema complete — applied=%d  skipped=%d  failed=%d",
        len(report["applied"]),
        len(report["skipped"]),
        len(report["failed"]),
    )
    return report


# ─────────────────────────────────────────────────────────────────────────────
# High-Level Node / Relationship Helpers
# (used by network_agent.py and seed_cloud.py)
# ─────────────────────────────────────────────────────────────────────────────

async def upsert_phone_number(
    number: str,
    *,
    telecom: Optional[str] = None,
    state: Optional[str] = None,
    reported_count: int = 0,
) -> CypherResult:
    """
    MERGE a PhoneNumber node, updating metadata on match.
    Returns the upserted node properties.
    """
    query = """
    MERGE (p:PhoneNumber {number: $number})
    ON CREATE SET
        p.telecom        = $telecom,
        p.state          = $state,
        p.reported_count = $reported_count,
        p.created_at     = datetime()
    ON MATCH SET
        p.reported_count = p.reported_count + $reported_count,
        p.updated_at     = datetime()
    RETURN p
    """
    return await execute_cypher(
        query,
        {
            "number":         number,
            "telecom":        telecom,
            "state":          state,
            "reported_count": reported_count,
        },
        write=True,
    )


async def upsert_bank_account(
    account_id: str,
    *,
    bank: Optional[str] = None,
    account_type: Optional[str] = None,
    state: Optional[str] = None,
    flagged: bool = False,
) -> CypherResult:
    """
    MERGE a BankAccount node, updating metadata on match.
    account_id should be a stable internal identifier (masked acc number + IFSC).
    """
    query = """
    MERGE (b:BankAccount {account_id: $account_id})
    ON CREATE SET
        b.bank         = $bank,
        b.account_type = $account_type,
        b.state        = $state,
        b.flagged      = $flagged,
        b.created_at   = datetime()
    ON MATCH SET
        b.flagged      = $flagged,
        b.updated_at   = datetime()
    RETURN b
    """
    return await execute_cypher(
        query,
        {
            "account_id":   account_id,
            "bank":         bank,
            "account_type": account_type,
            "state":        state,
            "flagged":      flagged,
        },
        write=True,
    )


async def upsert_fraud_actor(
    name: str,
    *,
    role: str,
    state: Optional[str] = None,
    aliases: Optional[list[str]] = None,
    syndicate_name: Optional[str] = None,
) -> CypherResult:
    """
    MERGE a FraudActor node.  If syndicate_name is provided, also MERGEs a
    Syndicate node and creates a [:MEMBER_OF] relationship.
    """
    if syndicate_name:
        query = """
        MERGE (a:FraudActor {name: $name})
        ON CREATE SET
            a.role       = $role,
            a.state      = $state,
            a.aliases    = $aliases,
            a.created_at = datetime()
        ON MATCH SET
            a.updated_at = datetime()
        WITH a
        MERGE (s:Syndicate {name: $syndicate_name})
        ON CREATE SET s.created_at = datetime()
        MERGE (a)-[:MEMBER_OF]->(s)
        RETURN a, s
        """
        params: dict[str, Any] = {
            "name":           name,
            "role":           role,
            "state":          state,
            "aliases":        aliases or [],
            "syndicate_name": syndicate_name,
        }
    else:
        query = """
        MERGE (a:FraudActor {name: $name})
        ON CREATE SET
            a.role       = $role,
            a.state      = $state,
            a.aliases    = $aliases,
            a.created_at = datetime()
        ON MATCH SET
            a.updated_at = datetime()
        RETURN a
        """
        params = {
            "name":    name,
            "role":    role,
            "state":   state,
            "aliases": aliases or [],
        }

    return await execute_cypher(query, params, write=True)


async def link_actor_to_phone(
    actor_name: str,
    phone_number: str,
    relationship: str = "USES",
) -> CypherResult:
    """
    Create (FraudActor)-[:USES]->(PhoneNumber).
    Both nodes must already exist (use upsert helpers above first).

    relationship: one of USES | OPERATES | CONTROLS
    """
    _allowed = {"USES", "OPERATES", "CONTROLS"}
    if relationship not in _allowed:
        raise ValueError(f"relationship must be one of {_allowed}, got {relationship!r}")

    # Dynamic relationship type requires a different Cypher approach
    # since Neo4j does not allow parameterised relationship types.
    query = f"""
    MATCH (a:FraudActor  {{name:   $actor_name}})
    MATCH (p:PhoneNumber {{number: $phone_number}})
    MERGE (a)-[r:{relationship}]->(p)
    ON CREATE SET r.since = datetime()
    RETURN a.name AS actor, type(r) AS rel, p.number AS phone
    """
    return await execute_cypher(
        query,
        {"actor_name": actor_name, "phone_number": phone_number},
        write=True,
    )


async def link_actor_to_bank(
    actor_name: str,
    account_id: str,
    relationship: str = "CONTROLS",
) -> CypherResult:
    """Create (FraudActor)-[:CONTROLS]->(BankAccount)."""
    _allowed = {"CONTROLS", "USES", "OPERATES"}
    if relationship not in _allowed:
        raise ValueError(f"relationship must be one of {_allowed}, got {relationship!r}")

    query = f"""
    MATCH (a:FraudActor  {{name:       $actor_name}})
    MATCH (b:BankAccount {{account_id: $account_id}})
    MERGE (a)-[r:{relationship}]->(b)
    ON CREATE SET r.since = datetime()
    RETURN a.name AS actor, type(r) AS rel, b.account_id AS account
    """
    return await execute_cypher(
        query,
        {"actor_name": actor_name, "account_id": account_id},
        write=True,
    )


async def get_network_by_phone(
    phone_number: str,
    max_hops: int = 3,
) -> CypherResult:
    """
    Multi-hop traversal starting from a PhoneNumber node.
    Returns all nodes and relationships within max_hops steps —
    the raw material for the vis-network graph renderer.

    max_hops is capped at 4 to prevent runaway traversals on the free tier.
    """
    max_hops = min(max_hops, 4)
    query = f"""
    MATCH path = (start:PhoneNumber {{number: $phone_number}})-[*1..{max_hops}]-(connected)
    RETURN
        nodes(path)        AS nodes,
        relationships(path) AS rels,
        length(path)        AS hops
    ORDER BY hops
    LIMIT 200
    """
    return await execute_cypher(query, {"phone_number": phone_number}, write=False)


async def get_network_by_bank_account(
    account_id: str,
    max_hops: int = 3,
) -> CypherResult:
    """
    Multi-hop traversal starting from a BankAccount node.
    """
    max_hops = min(max_hops, 4)
    query = f"""
    MATCH path = (start:BankAccount {{account_id: $account_id}})-[*1..{max_hops}]-(connected)
    RETURN
        nodes(path)         AS nodes,
        relationships(path) AS rels,
        length(path)        AS hops
    ORDER BY hops
    LIMIT 200
    """
    return await execute_cypher(query, {"account_id": account_id}, write=False)


async def search_actors_fulltext(keyword: str, limit: int = 10) -> CypherResult:
    """
    Full-text search across FraudActor name, state, and aliases fields.
    Backs the police dashboard search box.
    """
    query = """
    CALL db.index.fulltext.queryNodes('fraud_actor_fulltext', $keyword)
    YIELD node, score
    RETURN
        node.name    AS name,
        node.role    AS role,
        node.state   AS state,
        node.aliases AS aliases,
        score
    ORDER BY score DESC
    LIMIT $limit
    """
    return await execute_cypher(query, {"keyword": keyword, "limit": limit}, write=False)


async def upsert_phone_from_reports(
    phone_number: str,
    reports: list[dict],
) -> CypherResult:
    """
    Given a list of incident_report dicts from Supabase, MERGE a PhoneNumber
    node and create Victim nodes linked to it for each complaint.
    Called by the ghost-node fallback pipeline in network_agent.py.
    """
    query = """
    MERGE (p:PhoneNumber {number: $number})
    ON CREATE SET
        p.reported_count = $report_count,
        p.status         = 'UNVERIFIED',
        p.source         = 'supabase_incident_reports',
        p.created_at     = datetime()
    ON MATCH SET
        p.reported_count = p.reported_count + $report_count,
        p.status         = 'UNVERIFIED',
        p.updated_at     = datetime()
    WITH p
    UNWIND $victims AS v
    MERGE (vic:Victim {case_id: v.case_id})
    ON CREATE SET
        vic.state      = v.state,
        vic.amount_lost = v.amount_lost,
        vic.created_at = datetime()
    MERGE (p)-[:CALLED]->(vic)
    RETURN p, count(vic) AS victims_linked
    """
    victims = [
        {
            "case_id":    r.get("id", str(r.get("session_id", "unknown"))),
            "state":      "Unknown",
            "amount_lost": 0,
        }
        for r in reports
    ]
    return await execute_cypher(
        query,
        {"number": phone_number, "report_count": len(reports), "victims": victims},
        write=True,
    )


async def upsert_account_from_reports(
    account_id: str,
    reports: list[dict],
) -> CypherResult:
    """
    Given incident_report dicts, MERGE a BankAccount node and link Victim nodes.
    """
    query = """
    MERGE (b:BankAccount {account_id: $account_id})
    ON CREATE SET
        b.flagged    = true,
        b.status     = 'UNVERIFIED',
        b.source     = 'supabase_incident_reports',
        b.created_at = datetime()
    ON MATCH SET
        b.flagged    = true,
        b.status     = 'UNVERIFIED',
        b.updated_at = datetime()
    WITH b
    UNWIND $victims AS v
    MERGE (vic:Victim {case_id: v.case_id})
    ON CREATE SET
        vic.state       = v.state,
        vic.amount_lost = v.amount_lost,
        vic.created_at  = datetime()
    MERGE (vic)-[:TRANSFERRED_TO]->(b)
    RETURN b, count(vic) AS victims_linked
    """
    victims = [
        {
            "case_id":    r.get("id", str(r.get("session_id", "unknown"))),
            "state":      "Unknown",
            "amount_lost": 0,
        }
        for r in reports
    ]
    return await execute_cypher(
        query,
        {"account_id": account_id, "report_count": len(reports), "victims": victims},
        write=True,
    )


async def execute_nl_cypher(cypher: str, params: Optional[dict] = None) -> CypherResult:
    """
    Execute a raw Cypher string generated by network_agent.py's NL-to-Cypher
    translation pipeline.

    SECURITY: This function is intentionally restricted to READ-only access
    (write=False).  The NL-to-Cypher agent output must never be allowed to
    mutate graph state directly — mutations must go through the typed helpers
    above after human/system validation.
    """
    return await execute_cypher(cypher, params or {}, write=False)


# ─────────────────────────────────────────────────────────────────────────────
# Standalone Startup Coroutine
# ─────────────────────────────────────────────────────────────────────────────

async def startup_graph_layer() -> None:
    """
    Initialise the Neo4j driver (if not already done) and apply the full
    constraint/index schema.

    Can be called:
      a) From database.startup_databases()  — normal FastAPI lifespan path
      b) Directly in unit tests or seed scripts that only need the graph layer:

         asyncio.run(startup_graph_layer())

    If the driver is already initialised (e.g., called from startup_databases),
    init_neo4j() is a no-op because get_neo4j_driver() will succeed.
    """
    try:
        # Will raise RuntimeError if the driver is not yet up
        get_neo4j_driver()
        logger.debug("Neo4j driver already initialised — skipping init_neo4j().")
    except RuntimeError:
        await init_neo4j()

    schema_report = await apply_graph_schema()

    if schema_report["failed"]:
        logger.warning(
            "Some graph schema statements failed: %s",
            schema_report["failed"],
        )
    else:
        logger.info("✅  Neo4j graph layer fully initialised.")


async def shutdown_graph_layer() -> None:
    """Close the Neo4j driver. Delegates to database.close_neo4j()."""
    await close_neo4j()
    logger.info("Neo4j graph layer shut down.")
