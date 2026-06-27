"""
backend/api/routes/network.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SurakshaNet AI — Police Fraud Network Intelligence Routes
Phase 3 + Ghost-Node Enhancement  |  Model: Claude Sonnet 4.6 (1.3x)

Endpoints:
  POST /api/network/query                   — NL → Cypher → graph result
  POST /api/network/raw-cypher              — hand-written Cypher (read-only)
  GET  /api/network/trace/phone/{number}    — seeded traversal from phone number
  GET  /api/network/trace/account/{id}      — seeded traversal from bank account
  GET  /api/network/search/actors           — full-text FraudActor search

Ghost-Node Fallback Pipeline (for trace endpoints):
  1. Run normal graph traversal.
  2. If result is empty → query Supabase incident_reports for the identifier.
  3. If Supabase has records → MERGE nodes into Neo4j, re-run traversal.
  4. If Supabase also empty → return synthetic 1-node "UNVERIFIED ghost" result.
     Never throws a 503 for missing identifiers.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from agents.network_agent import (
    execute_nl_query,
    execute_raw_cypher,
    NetworkQueryResult,
    GraphNode,
    GraphEdge,
)
from services.neo4j_graph import (
    get_network_by_phone,
    get_network_by_bank_account,
    search_actors_fulltext,
    upsert_phone_from_reports,
    upsert_account_from_reports,
    CypherResult,
)
from services.database import pg_connection

logger = logging.getLogger("surakshanet.routes.network")

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Request bodies
# ─────────────────────────────────────────────────────────────────────────────

class NLQueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Natural language question from the police investigator",
        examples=["Find all mule accounts connected to Operator Alpha"],
    )


class RawCypherRequest(BaseModel):
    cypher: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Hand-written Cypher query (read-only; audited before execution)",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Supabase fallback — search incident_reports for a phone or account identifier
# ─────────────────────────────────────────────────────────────────────────────

async def _query_supabase_for_phone(phone_number: str) -> list[dict]:
    """
    Search Supabase incident_reports for any complaint that mentions this
    phone number in its raw_input text.
    Returns a list of matching report dicts (may be empty).
    Non-fatal — swallows DB errors and returns [].
    """
    try:
        async with pg_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, session_id, raw_input, verdict, risk_score, created_at
                FROM   incident_reports
                WHERE  raw_input ILIKE $1
                LIMIT  20
                """,
                f"%{phone_number}%",
            )
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("Supabase phone lookup failed (non-fatal): %s", exc)
        return []


async def _query_supabase_for_account(account_id: str) -> list[dict]:
    """
    Search Supabase incident_reports for complaints mentioning this account ID.
    """
    try:
        async with pg_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, session_id, raw_input, verdict, risk_score, created_at
                FROM   incident_reports
                WHERE  raw_input ILIKE $1
                LIMIT  20
                """,
                f"%{account_id}%",
            )
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("Supabase account lookup failed (non-fatal): %s", exc)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Ghost Node builder — when nothing exists anywhere
# ─────────────────────────────────────────────────────────────────────────────

def _build_ghost_node_result(
    identifier: str,
    node_label: str,           # "PhoneNumber" or "BankAccount"
    id_property: str,          # "number" or "account_id"
    question: str,
) -> NetworkQueryResult:
    """
    Construct a synthetic 1-node NetworkQueryResult when the identifier is
    found neither in Neo4j nor in Supabase.  The node carries status='UNVERIFIED'
    so the frontend can render it distinctly (grey ghost node).
    """
    ghost_id = f"ghost-{identifier}"
    ghost_node = GraphNode(
        id=ghost_id,
        label=node_label,
        properties={
            id_property: identifier,
            "status":    "UNVERIFIED",
            "source":    "ghost_node",
            "note":      (
                "This identifier has no recorded history in the SurakshaNet "
                "fraud intelligence database. It may be newly active or "
                "operating below the complaint threshold."
            ),
        },
    )
    return NetworkQueryResult(
        question=question,
        cypher_query=(
            f"MATCH (n:{node_label} {{{id_property}: $id}}) RETURN n  "
            f"// No results — ghost node synthesised"
        ),
        query_explanation=(
            f"No records found for {identifier} in Neo4j or Supabase incident reports. "
            "A synthetic UNVERIFIED ghost node was created for visualisation."
        ),
        is_safe=True,
        summary=(
            f"⚠ {identifier} has **no recorded history** in the SurakshaNet fraud "
            "database. This could mean: (1) the number is new and not yet reported, "
            "(2) victims have not filed formal complaints, or (3) it is a legitimate "
            "identifier. Treat as LOW PRIORITY until corroborating evidence emerges. "
            "Consider cross-checking with TRAI or the bank's internal fraud desk."
        ),
        nodes=[ghost_node],
        edges=[],
        row_count=0,
        model_used="ghost_node_synthesiser",
        processing_time_ms=0.0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# CypherResult → NetworkQueryResult projection
# ─────────────────────────────────────────────────────────────────────────────

def _cypher_result_to_network(
    cypher_result: CypherResult,
    question: str,
) -> NetworkQueryResult:
    """Wrap a raw CypherResult into a NetworkQueryResult for the frontend."""
    from agents.network_agent import _extract_graph_from_records

    nodes, edges = _extract_graph_from_records(cypher_result.records)
    row_count = len(cypher_result.records)

    if row_count == 0:
        summary = (
            "No matching records found for this identifier. "
            "It may not yet be catalogued in the fraud database."
        )
    else:
        summary = (
            f"Traversal complete — found {len(nodes)} unique entities "
            f"and {len(edges)} relationships in {cypher_result.elapsed_ms:.0f} ms."
        )

    return NetworkQueryResult(
        question=question,
        cypher_query=cypher_result.query,
        query_explanation="Pre-built seeded traversal query.",
        is_safe=True,
        summary=summary,
        nodes=nodes,
        edges=edges,
        row_count=row_count,
        model_used="neo4j_graph_helper",
        processing_time_ms=cypher_result.elapsed_ms,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Core ghost-node pipeline — shared by phone and account traces
# ─────────────────────────────────────────────────────────────────────────────

async def _trace_with_ghost_fallback(
    *,
    identifier: str,
    node_label: str,
    id_property: str,
    hops: int,
    question: str,
    fetch_from_neo4j,          # coroutine: (identifier, hops) → CypherResult
    upsert_from_reports,       # coroutine: (identifier, reports) → CypherResult
    fetch_supabase,            # coroutine: (identifier) → list[dict]
) -> NetworkQueryResult:
    """
    Full 4-stage pipeline:
      1. Query Neo4j — if nodes found, return immediately.
      2. Supabase fallback — if Neo4j empty, search incident_reports.
      3. Upsert + re-query — if Supabase found records, MERGE into graph and retry.
      4. Ghost node — if still nothing, return 1-node UNVERIFIED result.
    """
    import time
    t0 = time.monotonic()

    # ── Stage 1: Normal Neo4j traversal ──────────────────────────────────────
    try:
        neo4j_result = await fetch_from_neo4j(identifier, hops)
    except Exception as exc:
        logger.error("Neo4j traversal error for %s: %s", identifier, exc)
        # Don't propagate — fall through to Supabase stage
        neo4j_result = CypherResult(records=[], summary=None, elapsed_ms=0.0, query="")

    if neo4j_result.records:
        logger.info("Neo4j hit for %s — %d records", identifier, len(neo4j_result.records))
        result = _cypher_result_to_network(neo4j_result, question)
        result.processing_time_ms = round((time.monotonic() - t0) * 1000, 2)
        return result

    logger.info("Neo4j empty for %s — checking Supabase incident_reports", identifier)

    # ── Stage 2: Supabase fallback ────────────────────────────────────────────
    supabase_reports = await fetch_supabase(identifier)

    if not supabase_reports:
        # ── Stage 4: Ghost node ───────────────────────────────────────────────
        logger.info("No Supabase records for %s — synthesising ghost node", identifier)
        result = _build_ghost_node_result(identifier, node_label, id_property, question)
        result.processing_time_ms = round((time.monotonic() - t0) * 1000, 2)
        return result

    # ── Stage 3: Upsert evidence into Neo4j, then re-run traversal ───────────
    logger.info(
        "Supabase found %d reports for %s — upserting into Neo4j",
        len(supabase_reports), identifier,
    )
    try:
        await upsert_from_reports(identifier, supabase_reports)
        logger.info("Upsert complete for %s — re-running traversal", identifier)
        neo4j_retry = await fetch_from_neo4j(identifier, hops)
    except Exception as exc:
        logger.error("Upsert/re-query failed for %s: %s — returning ghost node", identifier, exc)
        result = _build_ghost_node_result(identifier, node_label, id_property, question)
        result.summary = (
            f"Found {len(supabase_reports)} historical complaint(s) for {identifier} in the "
            "incident database, but graph upsert encountered an error. "
            f"Details: {exc}. "
            "A ghost node is shown — please retry to trigger re-population."
        )
        result.processing_time_ms = round((time.monotonic() - t0) * 1000, 2)
        return result

    result = _cypher_result_to_network(neo4j_retry, question)
    result.summary = (
        f"📥 New evidence found: {len(supabase_reports)} historical complaint(s) for "
        f"{identifier} were retrieved from the incident database and merged into the "
        f"fraud graph. Traversal now shows {len(result.nodes)} connected entities. "
        "Node marked UNVERIFIED — verify with primary sources before taking action."
    )
    result.processing_time_ms = round((time.monotonic() - t0) * 1000, 2)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/query",
    response_model=NetworkQueryResult,
    summary="Natural language investigation query",
)
async def nl_query(body: NLQueryRequest) -> NetworkQueryResult:
    logger.info("NL query  chars=%d  preview=%r", len(body.question), body.question[:80])
    return await execute_nl_query(body.question)


@router.post(
    "/raw-cypher",
    response_model=NetworkQueryResult,
    summary="Execute a hand-written read-only Cypher query (advanced)",
)
async def raw_cypher_query(body: RawCypherRequest) -> NetworkQueryResult:
    logger.info("Raw Cypher request  preview=%r", body.cypher[:80])
    result = await execute_raw_cypher(body.cypher)
    if not result.is_safe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=result.summary,
        )
    return result


@router.get(
    "/trace/phone/{phone_number}",
    response_model=NetworkQueryResult,
    summary="Multi-hop traversal seeded from a phone number",
    description=(
        "Performs a graph traversal from the given phone number. "
        "If the number is not in the graph, automatically checks Supabase incident "
        "reports and upserts new evidence if found. Falls back to a ghost node if "
        "the number has no recorded history anywhere."
    ),
)
async def trace_by_phone(
    phone_number: str,
    hops: int = Query(default=3, ge=1, le=4, description="Traversal depth (1–4)"),
) -> NetworkQueryResult:
    number = unquote(phone_number).strip()
    if not number:
        raise HTTPException(status_code=422, detail="phone_number cannot be empty.")

    logger.info("Phone trace (ghost-aware)  number=%s  hops=%d", number, hops)

    return await _trace_with_ghost_fallback(
        identifier=number,
        node_label="PhoneNumber",
        id_property="number",
        hops=hops,
        question=f"Trace phone number {number} ({hops} hops)",
        fetch_from_neo4j=get_network_by_phone,
        upsert_from_reports=upsert_phone_from_reports,
        fetch_supabase=_query_supabase_for_phone,
    )


@router.get(
    "/trace/account/{account_id}",
    response_model=NetworkQueryResult,
    summary="Multi-hop traversal seeded from a bank account ID",
    description=(
        "Performs a graph traversal from the given bank account. "
        "If the account is not in the graph, checks Supabase and upserts evidence. "
        "Returns a ghost node if the account has no recorded history."
    ),
)
async def trace_by_account(
    account_id: str,
    hops: int = Query(default=3, ge=1, le=4, description="Traversal depth (1–4)"),
) -> NetworkQueryResult:
    aid = unquote(account_id).strip()
    if not aid:
        raise HTTPException(status_code=422, detail="account_id cannot be empty.")

    logger.info("Account trace (ghost-aware)  account=%s  hops=%d", aid, hops)

    return await _trace_with_ghost_fallback(
        identifier=aid,
        node_label="BankAccount",
        id_property="account_id",
        hops=hops,
        question=f"Trace bank account {aid} ({hops} hops)",
        fetch_from_neo4j=get_network_by_bank_account,
        upsert_from_reports=upsert_account_from_reports,
        fetch_supabase=_query_supabase_for_account,
    )


@router.get(
    "/search/actors",
    summary="Full-text search across FraudActor nodes",
)
async def search_actors(
    q: str    = Query(..., min_length=2, max_length=200, description="Search keyword"),
    limit: int = Query(default=10, ge=1, le=50, description="Max results"),
):
    logger.info("Actor search  q=%r  limit=%d", q, limit)
    try:
        result: CypherResult = await search_actors_fulltext(q, limit=limit)
    except Exception as exc:
        logger.error("Actor search failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Full-text search failed: {exc}",
        )
    return {
        "query":   q,
        "results": result.records,
        "count":   len(result.records),
    }
