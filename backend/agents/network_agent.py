"""
backend/agents/network_agent.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SurakshaNet AI — Phase 2: Police Intelligence NL-to-Cypher Agent
Model: Claude Sonnet 4.6 (1.3x) — Heavy NL→Cypher translation task

Acts as the translation layer between the police investigation dashboard
and the neo4j_graph.py service.

Two-stage LLM pipeline (per request):
  Stage A — Translate
    1. Natural-language question + Neo4j schema → Groq llama-3.3-70b-versatile.
    2. Model returns JSON containing cypher_query, query_explanation, is_safe.
    3. Multi-layer safety audit verifies cypher_query is strictly read-only.

  Stage B — Execute & Summarise
    4. If is_safe and audit passes, run the Cypher via neo4j_graph.execute_nl_cypher().
    5. Pass the raw records back to Groq for a plain-English forensic summary.
    6. Transform the records into vis-network-ready { nodes, edges } JSON for
       the frontend graph renderer.

Security:
  - Two independent layers reject mutation Cypher: the model self-audit
    (is_safe flag) AND a strict regex-based audit in this module.
  - neo4j_graph.execute_nl_cypher() is hard-coded write=False, providing a
    third defence in depth at the driver layer.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from typing import Any, Optional

from groq import AsyncGroq, APITimeoutError, RateLimitError, APIStatusError
from neo4j.exceptions import ClientError as Neo4jClientError
from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.neo4j_graph import execute_nl_cypher, CypherResult
from core.demo_responses import get_demo_network_response

logger = logging.getLogger("surakshanet.network_agent")

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

GROQ_API_KEY:   str  = os.environ["GROQ_API_KEY"]
DEMO_MOCK_MODE: bool = os.getenv("DEMO_MOCK_MODE", "false").lower() == "true"

# Phase 2 routing — NL-to-Cypher uses the 70B versatile model
GROQ_MODEL:        str   = "llama-3.3-70b-versatile"
GROQ_TIMEOUT:      float = 25.0
GROQ_MAX_TOKENS:   int   = 1024
GROQ_TEMP_TRANSLATE: float = 0.05   # near-deterministic for query generation
GROQ_TEMP_SUMMARY:   float = 0.25   # slightly warmer for natural-sounding summaries

# Hard cap on user question length — protects against prompt-injection bombs
MAX_QUESTION_CHARS: int = 1_000

# Hard cap on records returned to the summariser — protects token budget
MAX_RECORDS_FOR_SUMMARY: int = 50

# Hard cap on nodes/edges sent to frontend graph renderer
MAX_GRAPH_NODES: int = 150
MAX_GRAPH_EDGES: int = 300


# ─────────────────────────────────────────────────────────────────────────────
# Lazy singleton — shared Groq client
# ─────────────────────────────────────────────────────────────────────────────

_groq_client: Optional[AsyncGroq] = None


def _get_groq_client() -> AsyncGroq:
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncGroq(api_key=GROQ_API_KEY, timeout=GROQ_TIMEOUT)
        logger.info("Groq client initialised for NL-to-Cypher (model=%s)", GROQ_MODEL)
    return _groq_client


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas
# ─────────────────────────────────────────────────────────────────────────────

class CypherTranslation(BaseModel):
    """Intermediate model — raw output from Stage A translation call."""
    cypher_query:      str
    query_explanation: str
    is_safe:           bool

    @field_validator("cypher_query")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("cypher_query cannot be empty")
        return v.strip()


class GraphNode(BaseModel):
    """vis-network-compatible node payload sent to the frontend."""
    id:    str
    label: str                    # Neo4j label (FraudActor, PhoneNumber, etc.)
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """vis-network-compatible edge payload."""
    source: str
    target: str
    label:  str                   # Relationship type (USES, CONTROLS, ...)
    properties: dict[str, Any] = Field(default_factory=dict)


class NetworkQueryResult(BaseModel):
    """Canonical output contract for the police network query pipeline."""

    model_config = ConfigDict(protected_namespaces=())

    # ── Original input ──────────────────────────────────────────────────────
    question: str

    # ── Translation stage output ────────────────────────────────────────────
    cypher_query:      str
    query_explanation: str
    is_safe:           bool

    # ── Execution stage output ──────────────────────────────────────────────
    summary:    str = Field(default="")
    nodes:      list[GraphNode] = Field(default_factory=list)
    edges:      list[GraphEdge] = Field(default_factory=list)
    row_count:  int             = Field(default=0)

    # ── Pipeline metadata ───────────────────────────────────────────────────
    model_used:         str   = Field(default=GROQ_MODEL)
    processing_time_ms: float = Field(default=0.0)


# ─────────────────────────────────────────────────────────────────────────────
# Neo4j Schema Reference — injected verbatim into the translation prompt
# ─────────────────────────────────────────────────────────────────────────────
#
# Keep this string in sync with the constraints in services/neo4j_graph.py.
# The translator's accuracy depends on this being exactly correct.
# ─────────────────────────────────────────────────────────────────────────────

_NEO4J_SCHEMA_DESCRIPTION = """
NEO4J GRAPH SCHEMA — SurakshaNet Fraud Intelligence Database
═══════════════════════════════════════════════════════════════

NODE LABELS AND PROPERTIES:

(:PhoneNumber)
    • number          : STRING  (unique, format: '+91XXXXXXXXXX')
    • telecom         : STRING  ('Jio' | 'Airtel' | 'Vi' | 'BSNL')
    • state           : STRING  (Indian state circle of registration)
    • reported_count  : INTEGER (number of times reported in scam complaints)
    • created_at      : DATETIME

(:BankAccount)
    • account_id      : STRING  (unique, masked format: 'BANK-XXXXNNNN')
    • bank            : STRING  (e.g. 'SBI', 'HDFC', 'ICICI', 'Axis', 'PNB')
    • account_type    : STRING  ('savings' | 'current' | 'wallet')
    • state           : STRING
    • flagged         : BOOLEAN (true if flagged as mule account)

(:UPIId)
    • upi_id          : STRING  (unique, format: 'handle@provider')

(:FraudActor)
    • name            : STRING  (unique within case database)
    • role            : STRING  ('RINGLEADER' | 'MID_TIER' | 'MULE' | 'CALLER')
    • state           : STRING  (operating state)
    • aliases         : LIST<STRING>

(:Syndicate)
    • name            : STRING  (unique, e.g. 'Operation Jharkhand Ring')
    • description     : STRING

(:Victim)
    • case_id         : STRING  (unique, format: 'NCRB-YYYY-ST-NNNN')
    • state           : STRING
    • amount_lost     : INTEGER (₹ rupees, total reported)

═══════════════════════════════════════════════════════════════

RELATIONSHIP TYPES:

(:FraudActor)-[:USES]->(:PhoneNumber)
(:FraudActor)-[:OPERATES]->(:PhoneNumber | :UPIId)
(:FraudActor)-[:CONTROLS]->(:BankAccount)
(:FraudActor)-[:MEMBER_OF]->(:Syndicate)
(:FraudActor)-[:DIRECTS]->(:FraudActor)     // Ringleader → mid-tier handler
(:PhoneNumber)-[:CALLED]->(:Victim)
(:Victim)-[:TRANSFERRED_TO]->(:BankAccount)
(:Victim)-[:TRANSFERRED_TO]->(:UPIId)

All relationships may optionally carry a `since` DATETIME property.

═══════════════════════════════════════════════════════════════

AVAILABLE INDEXES (for ORDER BY / WHERE optimisation):
  • Full-text   : fraud_actor_fulltext  ON (FraudActor.name, .state, .aliases)
  • Full-text   : syndicate_fulltext    ON (Syndicate.name, .description)
  • Range       : PhoneNumber.created_at, BankAccount.bank, FraudActor.state
  • Range       : Victim.state, Victim.amount_lost
"""


# ─────────────────────────────────────────────────────────────────────────────
# Stage A — Translation system prompt
# ─────────────────────────────────────────────────────────────────────────────

def _build_translation_prompt() -> str:
    """Construct the NL→Cypher translator system prompt."""
    return f"""You are SurakshaNet's elite Cypher translation agent for the Indian Police Intelligence Dashboard. Your sole job is to convert a police investigator's plain-English question into a precise, READ-ONLY Neo4j Cypher query.

{_NEO4J_SCHEMA_DESCRIPTION}

TRANSLATION INSTRUCTIONS:
1. Read the investigator's question carefully.
2. Identify the seed entity (phone number, bank account, actor name, etc.).
3. Choose the smallest traversal that answers the question — never use more than 4 hops.
4. ALWAYS include a LIMIT clause (default LIMIT 100 if the question does not specify).
5. Prefer MATCH path = (...)-[*1..N]-(...) for multi-hop traversals and RETURN nodes(path), relationships(path) so the frontend can render the graph.
6. Use exact property names from the schema — never invent properties.
7. For text search on FraudActor, prefer the full-text index:
       CALL db.index.fulltext.queryNodes('fraud_actor_fulltext', $keyword) YIELD node, score

ABSOLUTE SECURITY RULES — VIOLATIONS MUST SET is_safe=false:
  • NEVER emit CREATE, MERGE, SET, DELETE, DETACH DELETE, REMOVE, DROP, CALL apoc.* mutations.
  • NEVER emit LOAD CSV, USING PERIODIC COMMIT, or any procedure that writes.
  • NEVER emit subqueries that mutate state (CALL { ... }).
  • If the question itself requests a mutation (e.g. "delete X", "create Y"), generate a placeholder MATCH query and set is_safe=false.

SELF-AUDIT PROTOCOL (is_safe flag):
  • Set is_safe=true ONLY if your generated cypher_query contains exclusively MATCH, OPTIONAL MATCH, WHERE, WITH, RETURN, ORDER BY, LIMIT, SKIP, UNWIND, CALL db.index.fulltext.queryNodes.
  • Set is_safe=false for anything else.
  • Be paranoid — when in doubt, set is_safe=false.

CRITICAL OUTPUT RULES:
- Respond with ONLY a single valid JSON object — no markdown, no prose.
- All string values properly escaped (use \\n inside cypher_query, not literal newlines).
- The JSON must exactly match:

{{
  "cypher_query": "<Cypher statement on a single logical line>",
  "query_explanation": "<2-3 sentence summary of what the query does and what it returns>",
  "is_safe": <true|false>
}}"""


# ─────────────────────────────────────────────────────────────────────────────
# Stage B — Summariser system prompt
# ─────────────────────────────────────────────────────────────────────────────

def _build_summary_prompt(question: str, cypher: str, row_count: int) -> str:
    """Construct the forensic-summary prompt — Stage B of the pipeline."""
    return f"""You are SurakshaNet's police forensic analyst AI. An investigator asked a question, the system generated and ran a Cypher query against the fraud intelligence graph, and now you must summarise the results in clear, actionable English for the investigator.

ORIGINAL QUESTION:
{question}

CYPHER QUERY EXECUTED:
{cypher}

RAW RESULT ROWS: {row_count}

YOUR JOB:
1. Read the JSON-formatted query results provided by the user message.
2. Identify the key entities, relationships, and patterns.
3. Highlight any red flags (mule accounts, multi-state operations, ringleader connections, high amount_lost figures).
4. Recommend 1-3 concrete investigative next steps where appropriate.
5. Write a concise summary — 3 to 6 sentences. Use Indian numbering (lakh / crore) when discussing rupee amounts.

OUTPUT RULES:
- Plain prose only — no JSON, no markdown headers, no bullet points unless listing 3+ items.
- Mention specific identifiers (phone numbers, account IDs, actor names) found in the results.
- If results are empty, say so plainly and suggest alternative search strategies.
- Stay factual — do not invent details that are not in the results."""


# ─────────────────────────────────────────────────────────────────────────────
# Cypher Safety Auditor — independent regex layer
# ─────────────────────────────────────────────────────────────────────────────
#
# Defence-in-depth: even if the LLM lies about is_safe, this layer catches
# any mutation keyword and forces is_safe=False before execution.
# ─────────────────────────────────────────────────────────────────────────────

# Word-boundary regex matching any Cypher write/mutation keyword. Case-insensitive.
_FORBIDDEN_CYPHER_KEYWORDS = re.compile(
    r"\b("
    r"CREATE|MERGE|SET|DELETE|DETACH|REMOVE|DROP|"
    r"LOAD\s+CSV|FOREACH|"
    r"CALL\s+apoc\.(?:create|refactor|merge|periodic|trigger)|"
    r"CALL\s+db\.(?:create|drop)|"
    r"USING\s+PERIODIC\s+COMMIT"
    r")\b",
    re.IGNORECASE,
)


def _audit_cypher_safety(cypher: str) -> tuple[bool, Optional[str]]:
    """
    Independent regex-based safety audit on a Cypher string.

    Returns (is_safe, reason_if_unsafe).
    Strips string literals before scanning so phrases like 'CREATE' inside a
    quoted property value don't cause false positives.
    """
    # Remove single- and double-quoted string literals — they may contain
    # words that look like keywords but are just data values.
    stripped = re.sub(r"'(?:[^'\\]|\\.)*'", "''", cypher)
    stripped = re.sub(r'"(?:[^"\\]|\\.)*"', '""', stripped)

    # Strip /* … */ block comments and // line comments
    stripped = re.sub(r"/\*[\s\S]*?\*/", " ", stripped)
    stripped = re.sub(r"//[^\n]*", " ", stripped)

    match = _FORBIDDEN_CYPHER_KEYWORDS.search(stripped)
    if match:
        return False, f"forbidden keyword detected: {match.group(0).upper()}"
    return True, None


# ─────────────────────────────────────────────────────────────────────────────
# JSON parsing helper — shared pattern from scam_agent / counterfeit_agent
# ─────────────────────────────────────────────────────────────────────────────

def _extract_json_object(raw: str) -> dict[str, Any]:
    """Strip markdown fences and surrounding prose, return parsed JSON."""
    cleaned = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    obj_match = re.search(r"\{[\s\S]+\}", cleaned)
    if obj_match:
        cleaned = obj_match.group(0)
    return json.loads(cleaned)


# ─────────────────────────────────────────────────────────────────────────────
# Stage A — Call Groq for NL→Cypher translation
# ─────────────────────────────────────────────────────────────────────────────

async def _call_groq_translate(question: str) -> CypherTranslation:
    """
    Stage A: convert the police officer's question into a Cypher query.
    Returns a validated CypherTranslation; raises on API or parse error.
    """
    client = _get_groq_client()
    system_prompt = _build_translation_prompt()

    response = await client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": f"Translate this investigator question into Cypher:\n\n{question}"},
        ],
        temperature=GROQ_TEMP_TRANSLATE,
        max_tokens=GROQ_MAX_TOKENS,
        response_format={"type": "json_object"},
        stream=False,
    )

    raw = response.choices[0].message.content or ""
    logger.debug(
        "Translation response  tokens=%d  finish=%s",
        response.usage.total_tokens if response.usage else -1,
        response.choices[0].finish_reason,
    )

    data = _extract_json_object(raw)
    return CypherTranslation(**data)


# ─────────────────────────────────────────────────────────────────────────────
# Stage B — Call Groq for plain-English summary of the result rows
# ─────────────────────────────────────────────────────────────────────────────

async def _call_groq_summarise(
    question: str,
    cypher: str,
    records: list[dict[str, Any]],
) -> str:
    """
    Stage B: forensic summary of result rows for the investigator.
    Returns plain prose; never raises (caller catches and falls back).
    """
    client = _get_groq_client()
    system_prompt = _build_summary_prompt(question, cypher, len(records))

    # Cap records sent to the summariser to protect the token budget
    capped_records = records[:MAX_RECORDS_FOR_SUMMARY]
    truncation_note = ""
    if len(records) > MAX_RECORDS_FOR_SUMMARY:
        truncation_note = (
            f"\n\n[Showing first {MAX_RECORDS_FOR_SUMMARY} of {len(records)} rows. "
            "Mention the truncation in your summary.]"
        )

    user_payload = (
        f"Result rows (JSON):\n{json.dumps(capped_records, default=str, indent=2)}"
        f"{truncation_note}"
    )

    response = await client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_payload},
        ],
        temperature=GROQ_TEMP_SUMMARY,
        max_tokens=GROQ_MAX_TOKENS,
        stream=False,
    )
    return (response.choices[0].message.content or "").strip()


# ─────────────────────────────────────────────────────────────────────────────
# Graph extraction — turn raw Cypher records into vis-network nodes/edges
# ─────────────────────────────────────────────────────────────────────────────

def _serialise_node(node: Any) -> Optional[GraphNode]:
    """
    Convert a neo4j.graph.Node (or already-dict-like row entry) into a GraphNode.
    Returns None if the object is not a node.
    """
    # neo4j.graph.Node exposes element_id, labels (frozenset), and dict-like access
    element_id = getattr(node, "element_id", None) or getattr(node, "id", None)
    labels     = getattr(node, "labels", None)

    if element_id is None or labels is None:
        return None

    # Pick the first concrete label — our schema never multi-labels a node
    label_str = next(iter(labels)) if labels else "Unknown"

    try:
        props = dict(node)
    except Exception:
        props = {}

    return GraphNode(
        id=str(element_id),
        label=label_str,
        properties={k: _coerce_property(v) for k, v in props.items()},
    )


def _serialise_relationship(rel: Any) -> Optional[GraphEdge]:
    """Convert a neo4j.graph.Relationship into a GraphEdge."""
    rel_type = getattr(rel, "type", None)
    start = getattr(rel, "start_node", None)
    end   = getattr(rel, "end_node",   None)

    if rel_type is None or start is None or end is None:
        return None

    source_id = getattr(start, "element_id", None) or getattr(start, "id", None)
    target_id = getattr(end,   "element_id", None) or getattr(end,   "id", None)
    if source_id is None or target_id is None:
        return None

    try:
        props = dict(rel)
    except Exception:
        props = {}

    return GraphEdge(
        source=str(source_id),
        target=str(target_id),
        label=rel_type,
        properties={k: _coerce_property(v) for k, v in props.items()},
    )


def _coerce_property(value: Any) -> Any:
    """JSON-safe coercion for Neo4j temporal types and other non-primitives."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_coerce_property(v) for v in value]
    # neo4j.time.DateTime, Date, etc. all have iso_format() or str()
    iso = getattr(value, "iso_format", None)
    if callable(iso):
        try:
            return iso()
        except Exception:
            pass
    return str(value)


def _extract_graph_from_records(records: list[dict[str, Any]]) -> tuple[list[GraphNode], list[GraphEdge]]:
    """
    Walk every value of every result row and pull out unique Neo4j nodes and
    relationships. Deduplication is by element_id.

    Handles three common Cypher return patterns:
      a) RETURN nodes(path), relationships(path)   → values are lists
      b) RETURN a, r, b                            → values are scalars
      c) Mixed                                      → both work
    """
    nodes_by_id: dict[str, GraphNode] = {}
    edges_by_id: dict[str, GraphEdge] = {}

    def _walk(item: Any) -> None:
        if item is None:
            return
        # Lists / tuples — recurse
        if isinstance(item, (list, tuple)):
            for sub in item:
                _walk(sub)
            return
        # Try node serialisation
        node = _serialise_node(item)
        if node is not None:
            nodes_by_id.setdefault(node.id, node)
            return
        # Try relationship serialisation
        edge = _serialise_relationship(item)
        if edge is not None:
            edge_key = f"{edge.source}->{edge.target}:{edge.label}"
            edges_by_id.setdefault(edge_key, edge)
            # Also auto-add endpoint nodes if they weren't returned separately
            for endpoint in (
                getattr(item, "start_node", None),
                getattr(item, "end_node",   None),
            ):
                ep_node = _serialise_node(endpoint) if endpoint is not None else None
                if ep_node is not None:
                    nodes_by_id.setdefault(ep_node.id, ep_node)

    for record in records:
        for value in record.values():
            _walk(value)

    # Apply size caps before returning to the frontend
    nodes = list(nodes_by_id.values())[:MAX_GRAPH_NODES]
    edges = list(edges_by_id.values())[:MAX_GRAPH_EDGES]

    # Drop any edge whose endpoints didn't survive the node cap
    valid_ids = {n.id for n in nodes}
    edges = [e for e in edges if e.source in valid_ids and e.target in valid_ids]

    return nodes, edges


def _records_to_jsonable(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Flatten records for the summariser:
      - Neo4j Node → {'_label': 'FraudActor', 'name': ..., 'role': ...}
      - Neo4j Relationship → {'_type': 'CONTROLS', ...properties}
      - Temporals → ISO strings
    """
    def _flatten(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (list, tuple)):
            return [_flatten(v) for v in value]

        node = _serialise_node(value)
        if node is not None:
            return {"_label": node.label, **node.properties}

        edge = _serialise_relationship(value)
        if edge is not None:
            return {"_type": edge.label, **edge.properties}

        return _coerce_property(value)

    return [{k: _flatten(v) for k, v in r.items()} for r in records]


# ─────────────────────────────────────────────────────────────────────────────
# Fallback construction
# ─────────────────────────────────────────────────────────────────────────────

def _guess_network_hint(question: str) -> str:
    """Keyword-based hint for demo-mode fixture selection."""
    q = question.lower()
    if any(kw in q for kw in ["delete", "remove", "drop", "create", "merge", "set "]):
        return "unsafe"
    if any(kw in q for kw in ["phone", "+91", "number", "mobile", "sim"]):
        return "phone"
    if any(kw in q for kw in ["actor", "alpha", "ringleader", "operator", "mule", "handler", "syndicate"]):
        return "actor"
    return "default"


def _fallback_result(
    question: str,
    translation: Optional[CypherTranslation],
    t_start: float,
    reason: str = "unknown",
) -> NetworkQueryResult:
    """
    Safe fallback when the live pipeline fails.
    DEMO_MOCK_MODE → canned fixture; production → empty-result NetworkQueryResult.
    """
    elapsed_ms = round((time.monotonic() - t_start) * 1000, 2)
    logger.warning("Network fallback  reason=%s  elapsed=%.0f ms", reason, elapsed_ms)

    if DEMO_MOCK_MODE:
        hint = _guess_network_hint(question)
        demo = get_demo_network_response(hint)
        demo["question"]           = question
        demo["processing_time_ms"] = elapsed_ms
        demo["model_used"]         = f"demo_fallback:{reason}"
        # Re-cast nodes/edges to Pydantic models
        demo["nodes"] = [
            GraphNode(
                id=n.get("id", str(uuid.uuid4())),
                label=n.get("label", "Unknown"),
                properties={k: v for k, v in n.items() if k not in {"id", "label"}},
            )
            for n in demo.get("nodes", [])
        ]
        demo["edges"] = [
            GraphEdge(
                source=e["source"],
                target=e["target"],
                label=e.get("label", "RELATED"),
                properties={k: v for k, v in e.items() if k not in {"source", "target", "label"}},
            )
            for e in demo.get("edges", [])
        ]
        return NetworkQueryResult(**demo)

    # Production fallback — preserve any translation we already have
    cypher_query      = translation.cypher_query      if translation else ""
    query_explanation = translation.query_explanation if translation else ""
    is_safe           = translation.is_safe           if translation else False

    return NetworkQueryResult(
        question=question,
        cypher_query=cypher_query,
        query_explanation=query_explanation,
        is_safe=is_safe,
        summary=(
            "The graph intelligence service is temporarily unavailable "
            f"(reason: {reason}). No results could be retrieved from the fraud "
            "database. Please try again in a few minutes or contact the system "
            "administrator if this persists."
        ),
        nodes=[],
        edges=[],
        row_count=0,
        model_used=f"fallback:{reason}",
        processing_time_ms=elapsed_ms,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API — execute_nl_query()
# ─────────────────────────────────────────────────────────────────────────────

async def execute_nl_query(question: str) -> NetworkQueryResult:
    """
    Full NL-to-Cypher pipeline for the police intelligence dashboard.

    Stages:
      A — Translate question to Cypher (Groq llama-3.3-70b-versatile).
      A.5 — Independent regex safety audit (defence in depth).
      B — Execute Cypher via neo4j_graph (write=False enforced at driver layer).
      C — Summarise raw results into plain English for the investigator.
      D — Project records into vis-network nodes + edges for the frontend.

    Never raises. All failures route through _fallback_result().
    """
    t_start = time.monotonic()
    question = (question or "").strip()
    translation: Optional[CypherTranslation] = None

    # ── Input guards ────────────────────────────────────────────────────────
    if not question:
        return NetworkQueryResult(
            question="",
            cypher_query="",
            query_explanation="",
            is_safe=False,
            summary="No question was provided.",
            processing_time_ms=round((time.monotonic() - t_start) * 1000, 2),
        )

    if len(question) > MAX_QUESTION_CHARS:
        logger.warning("Question truncated from %d to %d chars",
                       len(question), MAX_QUESTION_CHARS)
        question = question[:MAX_QUESTION_CHARS]

    # ── Demo / mock shortcut ────────────────────────────────────────────────
    if DEMO_MOCK_MODE:
        logger.info("DEMO_MOCK_MODE active — returning canned network response.")
        hint = _guess_network_hint(question)
        demo = get_demo_network_response(hint)
        demo["question"]           = question
        demo["processing_time_ms"] = round((time.monotonic() - t_start) * 1000, 2)
        demo["nodes"] = [
            GraphNode(
                id=n.get("id", str(uuid.uuid4())),
                label=n.get("label", "Unknown"),
                properties={k: v for k, v in n.items() if k not in {"id", "label"}},
            )
            for n in demo.get("nodes", [])
        ]
        demo["edges"] = [
            GraphEdge(
                source=e["source"],
                target=e["target"],
                label=e.get("label", "RELATED"),
                properties={k: v for k, v in e.items() if k not in {"source", "target", "label"}},
            )
            for e in demo.get("edges", [])
        ]
        return NetworkQueryResult(**demo)


    # ── Live pipeline ───────────────────────────────────────────────────────
    try:
        # ── Stage A: translate ─────────────────────────────────────────────
        translation = await _call_groq_translate(question)
        logger.info(
            "Translation OK  is_safe=%s  cypher_preview=%r",
            translation.is_safe,
            translation.cypher_query[:80],
        )

        # ── Stage A.5: independent regex safety audit ──────────────────────
        regex_safe, unsafe_reason = _audit_cypher_safety(translation.cypher_query)
        final_safe = translation.is_safe and regex_safe

        if not final_safe:
            audit_msg = (
                "Query rejected by the safety auditor — only read-only "
                "queries are permitted on the Police Intelligence Dashboard."
            )
            if not regex_safe:
                audit_msg += f" (auditor: {unsafe_reason})"
                logger.warning("Cypher audit blocked query: %s", unsafe_reason)

            return NetworkQueryResult(
                question=question,
                cypher_query=translation.cypher_query,
                query_explanation=translation.query_explanation,
                is_safe=False,
                summary=audit_msg,
                processing_time_ms=round((time.monotonic() - t_start) * 1000, 2),
            )

        # ── Stage B: execute Cypher (write=False enforced inside neo4j_graph) ─
        try:
            cypher_result: CypherResult = await execute_nl_cypher(translation.cypher_query)
        except Neo4jClientError as exc:
            # Bad Cypher syntax — surface a clean error to the user
            logger.error("Cypher syntax error: %s", exc)
            return NetworkQueryResult(
                question=question,
                cypher_query=translation.cypher_query,
                query_explanation=translation.query_explanation,
                is_safe=True,
                summary=(
                    "The generated Cypher query was syntactically invalid for "
                    "the current schema. Please rephrase your question and try "
                    f"again. (Neo4j: {exc.code or 'syntax_error'})"
                ),
                processing_time_ms=round((time.monotonic() - t_start) * 1000, 2),
            )

        raw_records = cypher_result.records
        row_count   = len(raw_records)
        logger.info(
            "Cypher executed  rows=%d  neo4j_ms=%.1f",
            row_count, cypher_result.elapsed_ms,
        )

        # ── Stage D: extract nodes/edges for frontend ──────────────────────
        nodes, edges = _extract_graph_from_records(raw_records)

        # ── Stage C: summarise results ─────────────────────────────────────
        if row_count == 0:
            summary = (
                "No matching records were found in the fraud graph for this "
                "query. The seed identifier may not yet be catalogued, or it "
                "has no recorded connections to known cases. Try a different "
                "identifier, a partial match, or widen the hop count."
            )
        else:
            try:
                jsonable_records = _records_to_jsonable(raw_records)
                summary = await _call_groq_summarise(
                    question, translation.cypher_query, jsonable_records
                )
            except Exception as sum_exc:
                # Summarisation failure is non-fatal — return raw counts instead
                logger.warning("Summary stage failed (non-fatal): %s", sum_exc)
                summary = (
                    f"Retrieved {row_count} result row(s) and {len(nodes)} unique "
                    f"entities with {len(edges)} relationships. (Plain-English "
                    "summarisation was unavailable for this query.)"
                )

        elapsed_ms = round((time.monotonic() - t_start) * 1000, 2)
        result = NetworkQueryResult(
            question=question,
            cypher_query=translation.cypher_query,
            query_explanation=translation.query_explanation,
            is_safe=True,
            summary=summary,
            nodes=nodes,
            edges=edges,
            row_count=row_count,
            model_used=GROQ_MODEL,
            processing_time_ms=elapsed_ms,
        )

        logger.info(
            "NetworkQuery complete  rows=%d  nodes=%d  edges=%d  elapsed=%.0f ms",
            row_count, len(nodes), len(edges), elapsed_ms,
        )
        return result


    # ── Granular exception handling — mirrors scam/counterfeit agents ───────
    except (APITimeoutError, asyncio.TimeoutError) as exc:
        logger.error("Groq timeout in network agent: %s", exc)
        return _fallback_result(question, translation, t_start, reason="groq_timeout")

    except RateLimitError as exc:
        logger.error("Groq rate limit in network agent: %s", exc)
        return _fallback_result(question, translation, t_start, reason="groq_rate_limit")

    except APIStatusError as exc:
        logger.error("Groq API error %d: %s", exc.status_code, exc)
        return _fallback_result(question, translation, t_start, reason=f"groq_api_{exc.status_code}")

    except json.JSONDecodeError as exc:
        logger.error("Translation JSON parse error: %s", exc)
        return _fallback_result(question, translation, t_start, reason="json_parse_error")

    except Exception as exc:
        logger.exception("Unexpected error in execute_nl_query: %s", exc)
        return _fallback_result(question, translation, t_start, reason="unexpected_error")


# ─────────────────────────────────────────────────────────────────────────────
# Convenience wrapper — direct Cypher execution path
# ─────────────────────────────────────────────────────────────────────────────

async def execute_raw_cypher(cypher: str) -> NetworkQueryResult:
    """
    Bypass Stage A and run a pre-written Cypher string. Still subject to the
    independent regex safety audit and the driver-level write=False enforcement.

    Intended for advanced police users who want to run hand-crafted queries
    via a 'developer mode' input in the dashboard.
    """
    t_start = time.monotonic()
    cypher  = (cypher or "").strip()

    if not cypher:
        return NetworkQueryResult(
            question=cypher,
            cypher_query="",
            query_explanation="",
            is_safe=False,
            summary="Empty Cypher query.",
        )

    regex_safe, reason = _audit_cypher_safety(cypher)
    if not regex_safe:
        return NetworkQueryResult(
            question=cypher,
            cypher_query=cypher,
            query_explanation="Raw Cypher submitted directly by the user.",
            is_safe=False,
            summary=f"Query rejected by safety auditor: {reason}",
            processing_time_ms=round((time.monotonic() - t_start) * 1000, 2),
        )

    try:
        cypher_result = await execute_nl_cypher(cypher)
        nodes, edges = _extract_graph_from_records(cypher_result.records)
        return NetworkQueryResult(
            question=cypher,
            cypher_query=cypher,
            query_explanation="Raw Cypher submitted directly by the user.",
            is_safe=True,
            summary=f"Executed raw Cypher. Returned {len(cypher_result.records)} row(s).",
            nodes=nodes,
            edges=edges,
            row_count=len(cypher_result.records),
            model_used="raw_cypher",
            processing_time_ms=round((time.monotonic() - t_start) * 1000, 2),
        )
    except Exception as exc:
        logger.exception("Raw Cypher execution failed: %s", exc)
        return _fallback_result(cypher, None, t_start, reason=f"raw_cypher_error:{type(exc).__name__}")
