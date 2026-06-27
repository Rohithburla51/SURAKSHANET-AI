"""
backend/services/database.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SurakshaNet AI — Phase 1: Relational & Graph Storage Layer
Model: Claude Sonnet 4.6 (1.3x) — Heavy DB/Schema task

Responsibilities:
  • Async connection pool to Supabase PostgreSQL via asyncpg
  • pgvector extension bootstrap + known_scams schema DDL
  • Neo4j Aura TLS connection pool via the official async driver
  • Explicit node/relationship constraints for the fraud graph
  • Health-check helpers used by /health endpoint
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from neo4j import AsyncGraphDatabase, AsyncDriver
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────────────────
# Environment & Logging
# ─────────────────────────────────────────────────────────────────────────────

load_dotenv()

logger = logging.getLogger("surakshanet.database")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration — pulled exclusively from environment, never hard-coded
# ─────────────────────────────────────────────────────────────────────────────

DATABASE_URL: str = os.environ["DATABASE_URL"]          # postgresql://user:pass@host:5432/db
NEO4J_URI: str    = os.environ["NEO4J_URI"]             # neo4j+s://xxxx.databases.neo4j.io
NEO4J_USER: str   = os.environ["NEO4J_USER"]
NEO4J_PASSWORD: str = os.environ["NEO4J_PASSWORD"]

# asyncpg pool tuning
PG_POOL_MIN_SIZE: int = 2
PG_POOL_MAX_SIZE: int = 10
PG_COMMAND_TIMEOUT: float = 30.0   # seconds

# ─────────────────────────────────────────────────────────────────────────────
# Module-level singletons  (populated during app lifespan startup)
# ─────────────────────────────────────────────────────────────────────────────

_pg_pool: Optional[asyncpg.Pool] = None
_neo4j_driver: Optional[AsyncDriver] = None


# ─────────────────────────────────────────────────────────────────────────────
# PostgreSQL — asyncpg connection pool
# ─────────────────────────────────────────────────────────────────────────────

async def init_postgres() -> asyncpg.Pool:
    """
    Create and warm up the asyncpg connection pool.
    Registers a custom codec so Python lists are transparently
    converted to/from the pgvector 'vector' type.
    """
    global _pg_pool

    logger.info("Initialising Supabase PostgreSQL connection pool …")

    async def _set_codec(conn: asyncpg.Connection) -> None:
        """
        asyncpg does not know the 'vector' type natively.
        We register a text codec that serialises Python list[float] to
        the pgvector wire format '[0.1,0.2, ...]' and back.
        """
        await conn.set_type_codec(
            "vector",
            encoder=lambda v: "[" + ",".join(str(x) for x in v) + "]",
            decoder=lambda s: [float(x) for x in s.strip("[]").split(",")],
            schema="public",
            format="text",
        )

    _pg_pool = await asyncpg.create_pool(
        dsn=DATABASE_URL,
        min_size=PG_POOL_MIN_SIZE,
        max_size=PG_POOL_MAX_SIZE,
        command_timeout=PG_COMMAND_TIMEOUT,
        init=_set_codec,
        ssl="require",         # Supabase enforces TLS
    )

    logger.info(
        "PostgreSQL pool ready  (min=%d  max=%d)",
        PG_POOL_MIN_SIZE,
        PG_POOL_MAX_SIZE,
    )
    return _pg_pool


async def close_postgres() -> None:
    """Gracefully drain and close the PostgreSQL pool."""
    global _pg_pool
    if _pg_pool:
        await _pg_pool.close()
        _pg_pool = None
        logger.info("PostgreSQL pool closed.")


def get_pg_pool() -> asyncpg.Pool:
    """
    FastAPI dependency — returns the live pool or raises if startup
    did not complete.
    """
    if _pg_pool is None:
        raise RuntimeError(
            "PostgreSQL pool is not initialised. "
            "Ensure init_postgres() was called during app lifespan startup."
        )
    return _pg_pool


@asynccontextmanager
async def pg_connection():
    """
    Async context manager that checks out one connection from the pool
    and returns it on exit, even if an exception is raised.

    Usage:
        async with pg_connection() as conn:
            row = await conn.fetchrow("SELECT ...")
    """
    pool = get_pg_pool()
    async with pool.acquire() as conn:
        yield conn


# ─────────────────────────────────────────────────────────────────────────────
# PostgreSQL — Schema Bootstrap (pgvector + known_scams)
# ─────────────────────────────────────────────────────────────────────────────

_SCHEMA_DDL = """
-- Enable the pgvector extension (idempotent)
CREATE EXTENSION IF NOT EXISTS vector;

-- ── Scam knowledge base for RAG ─────────────────────────────────────────────
-- Stores real-world Indian cybercrime text samples with 384-dim embeddings
-- produced by all-MiniLM-L6-v2. The <=> operator is cosine distance.
CREATE TABLE IF NOT EXISTS known_scams (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    category    VARCHAR(64) NOT NULL,          -- e.g. 'digital_arrest', 'kyc_phishing'
    raw_text    TEXT        NOT NULL,
    language    VARCHAR(8)  NOT NULL DEFAULT 'en',   -- 'en' | 'hi' | 'te' | etc.
    risk_score  SMALLINT    NOT NULL DEFAULT 90      -- baseline severity 0-100
                CHECK (risk_score BETWEEN 0 AND 100),
    source      VARCHAR(128),                        -- e.g. 'NCRB', 'I4C', 'manual'
    embedding   vector(384),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- IVFFlat index for approximate nearest-neighbour vector search.
-- lists=100 is appropriate for tables up to ~1 million rows.
CREATE INDEX IF NOT EXISTS known_scams_embedding_idx
    ON known_scams
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Ordinary B-tree indexes for common filter columns
CREATE INDEX IF NOT EXISTS known_scams_category_idx ON known_scams (category);
CREATE INDEX IF NOT EXISTS known_scams_language_idx ON known_scams (language);

-- ── Incident reports (citizen submissions) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS incident_reports (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID        NOT NULL,
    input_type      VARCHAR(16) NOT NULL CHECK (input_type IN ('text', 'audio', 'image')),
    raw_input       TEXT,
    risk_score      SMALLINT    CHECK (risk_score BETWEEN 0 AND 100),
    verdict         VARCHAR(32),               -- 'SCAM' | 'LIKELY_SCAM' | 'SAFE'
    explanation_en  TEXT,
    explanation_hi  TEXT,
    top_match_id    UUID REFERENCES known_scams(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Counterfeit scan log (bank teller portal) ───────────────────────────────
CREATE TABLE IF NOT EXISTS counterfeit_scans (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_code     VARCHAR(32),
    denomination    SMALLINT,                  -- 100 | 200 | 500 | 2000
    verdict         VARCHAR(16) NOT NULL CHECK (verdict IN ('GENUINE', 'SUSPECT', 'COUNTERFEIT')),
    confidence      NUMERIC(5,4),              -- 0.0000 – 1.0000
    opencv_flags    JSONB,                     -- edge/FFT/laplacian metrics
    llava_response  TEXT,
    scanned_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


async def bootstrap_schema() -> None:
    """
    Idempotently create the pgvector extension and all application tables.
    Safe to call on every startup — uses IF NOT EXISTS throughout.
    """
    logger.info("Running schema bootstrap (idempotent) …")
    async with pg_connection() as conn:
        await conn.execute(_SCHEMA_DDL)
    logger.info("Schema bootstrap complete.")


# ─────────────────────────────────────────────────────────────────────────────
# Neo4j Aura — Async Driver
# ─────────────────────────────────────────────────────────────────────────────

async def init_neo4j() -> AsyncDriver:
    """
    Initialise the Neo4j Aura async driver over the native
    bolt+TLS (neo4j+s://) transport.

    The driver manages its own internal connection pool; we verify
    connectivity immediately so startup fails fast if credentials are wrong.
    """
    global _neo4j_driver

    logger.info("Connecting to Neo4j Aura Graph DB …")

    _neo4j_driver = AsyncGraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
        # Keep connections alive — Aura has a 60-second idle timeout on free tier
        connection_timeout=15,
        max_connection_lifetime=3600,
        max_connection_pool_size=25,
        fetch_size=200,
    )

    # Verify the connection is reachable
    await _neo4j_driver.verify_connectivity()
    logger.info("Neo4j Aura connection verified.")
    return _neo4j_driver


async def close_neo4j() -> None:
    """Close all pooled Neo4j connections."""
    global _neo4j_driver
    if _neo4j_driver:
        await _neo4j_driver.close()
        _neo4j_driver = None
        logger.info("Neo4j driver closed.")


def get_neo4j_driver() -> AsyncDriver:
    """FastAPI dependency — returns the live driver or raises."""
    if _neo4j_driver is None:
        raise RuntimeError(
            "Neo4j driver is not initialised. "
            "Ensure init_neo4j() was called during app lifespan startup."
        )
    return _neo4j_driver


# ─────────────────────────────────────────────────────────────────────────────
# Neo4j — Graph Schema Constraints & Indexes
# ─────────────────────────────────────────────────────────────────────────────

_NEO4J_CONSTRAINTS: list[str] = [
    # Uniqueness constraints (also create a backing index automatically)
    "CREATE CONSTRAINT fraud_actor_name IF NOT EXISTS "
    "FOR (a:FraudActor) REQUIRE a.name IS UNIQUE",

    "CREATE CONSTRAINT phone_number_unique IF NOT EXISTS "
    "FOR (p:PhoneNumber) REQUIRE p.number IS UNIQUE",

    "CREATE CONSTRAINT bank_account_unique IF NOT EXISTS "
    "FOR (b:BankAccount) REQUIRE b.account_id IS UNIQUE",

    "CREATE CONSTRAINT upi_id_unique IF NOT EXISTS "
    "FOR (u:UPIId) REQUIRE u.upi_id IS UNIQUE",

    "CREATE CONSTRAINT victim_id_unique IF NOT EXISTS "
    "FOR (v:Victim) REQUIRE v.case_id IS UNIQUE",

    "CREATE CONSTRAINT syndicate_name_unique IF NOT EXISTS "
    "FOR (s:Syndicate) REQUIRE s.name IS UNIQUE",

    # Property existence constraints — enforce non-null on key fields
    "CREATE CONSTRAINT fraud_actor_role IF NOT EXISTS "
    "FOR (a:FraudActor) REQUIRE a.role IS NOT NULL",

    "CREATE CONSTRAINT phone_number_not_null IF NOT EXISTS "
    "FOR (p:PhoneNumber) REQUIRE p.number IS NOT NULL",
]

_NEO4J_INDEXES: list[str] = [
    # Full-text index enables keyword search across actor names and states
    "CREATE FULLTEXT INDEX fraud_actor_fulltext IF NOT EXISTS "
    "FOR (a:FraudActor) ON EACH [a.name, a.state, a.aliases]",

    # Range index for date-range queries on incidents
    "CREATE INDEX phone_created_at IF NOT EXISTS "
    "FOR (p:PhoneNumber) ON (p.created_at)",

    "CREATE INDEX bank_account_bank IF NOT EXISTS "
    "FOR (b:BankAccount) ON (b.bank)",
]


async def bootstrap_graph_schema() -> None:
    """
    Apply all uniqueness constraints and indexes to the Neo4j Aura instance.
    Idempotent — uses IF NOT EXISTS throughout.
    """
    driver = get_neo4j_driver()
    logger.info("Applying Neo4j graph constraints and indexes …")

    async with driver.session(database="neo4j") as session:
        for statement in _NEO4J_CONSTRAINTS + _NEO4J_INDEXES:
            try:
                await session.run(statement)
                logger.debug("Applied: %s", statement[:80])
            except Exception as exc:
                # Non-fatal: log and continue — constraint may already exist
                # under a different internal name in older Aura versions.
                logger.warning("Graph schema statement skipped: %s | %s", exc, statement[:60])

    logger.info("Neo4j graph schema bootstrap complete.")


# ─────────────────────────────────────────────────────────────────────────────
# Unified Startup / Shutdown  (called from FastAPI lifespan)
# ─────────────────────────────────────────────────────────────────────────────

async def startup_databases() -> None:
    """
    Initialise all storage backends in parallel, then run schema bootstraps.
    Call this inside the FastAPI @asynccontextmanager lifespan before yield.

    Example usage in main.py:
        from contextlib import asynccontextmanager
        from services.database import startup_databases, shutdown_databases

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await startup_databases()
            yield
            await shutdown_databases()

        app = FastAPI(lifespan=lifespan)
    """
    # Initialise connections concurrently to reduce startup time
    pg_task    = asyncio.create_task(init_postgres())
    neo4j_task = asyncio.create_task(init_neo4j())

    await asyncio.gather(pg_task, neo4j_task)

    # Schema bootstraps run after pools are confirmed live
    await asyncio.gather(
        bootstrap_schema(),
        bootstrap_graph_schema(),
    )

    logger.info("✅  All storage backends online.")


async def shutdown_databases() -> None:
    """Gracefully close all database connections. Call after lifespan yield."""
    await asyncio.gather(
        close_postgres(),
        close_neo4j(),
    )
    logger.info("All storage backends closed.")


# ─────────────────────────────────────────────────────────────────────────────
# Health Check Helpers  (used by GET /health)
# ─────────────────────────────────────────────────────────────────────────────

async def health_check_postgres() -> dict:
    """Return {'status': 'ok', 'latency_ms': float} or {'status': 'error', 'detail': str}."""
    import time
    try:
        t0 = time.monotonic()
        async with pg_connection() as conn:
            await conn.fetchval("SELECT 1")
        latency_ms = round((time.monotonic() - t0) * 1000, 2)
        return {"status": "ok", "latency_ms": latency_ms}
    except Exception as exc:
        logger.error("PostgreSQL health check failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


async def health_check_neo4j() -> dict:
    """Return {'status': 'ok', 'latency_ms': float} or {'status': 'error', 'detail': str}."""
    import time
    try:
        driver = get_neo4j_driver()
        t0 = time.monotonic()
        async with driver.session(database="neo4j") as session:
            await session.run("RETURN 1")
        latency_ms = round((time.monotonic() - t0) * 1000, 2)
        return {"status": "ok", "latency_ms": latency_ms}
    except Exception as exc:
        logger.error("Neo4j health check failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


async def health_check_all() -> dict:
    """Aggregate health status for both storage backends."""
    pg_status, neo4j_status = await asyncio.gather(
        health_check_postgres(),
        health_check_neo4j(),
    )
    overall = "ok" if pg_status["status"] == "ok" and neo4j_status["status"] == "ok" else "degraded"
    return {
        "overall": overall,
        "postgres": pg_status,
        "neo4j": neo4j_status,
    }
