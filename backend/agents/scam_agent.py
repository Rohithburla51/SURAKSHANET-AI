"""
backend/agents/scam_agent.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SurakshaNet AI — Phase 2: Scam Analysis Agent
Model: Claude Sonnet 4.6 (1.3x) — Heavy inference + pgvector RAG task

Pipeline (per request):
  1. Embed the user input text via sentence-transformers (all-MiniLM-L6-v2)
     running locally on CPU — zero API cost, deterministic, <50 ms.
  2. Pull the top-3 most semantically similar scams from Supabase `known_scams`
     table using the pgvector cosine-distance operator (<=>).
  3. Construct a precision-engineered system prompt that injects the RAG context
     and forces the 120B model to classify Indian scam types and map psychological
     manipulation tactics.
  4. Call Groq's `openai/gpt-oss-120b` with strict JSON mode to produce a
     structured ScamAnalysisResult.
  5. Validate and parse the JSON response against the Pydantic schema.
  6. Persist the result to Supabase `incident_reports`.
  7. On any failure (Groq timeout, DB error, parse error): if DEMO_MOCK_MODE is
     enabled fall back to a pre-baked response from core/demo_responses.py;
     otherwise re-raise so the API route can return a 503.

Security notes:
  - User input is never interpolated into Cypher or SQL strings; it travels
    through parameterised queries only.
  - The Groq response is parsed through Pydantic before any field is trusted.
  - risk_score is clamped to [0, 100] after parsing to guard against model drift.
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
from pydantic import BaseModel, Field, field_validator, model_validator
from sentence_transformers import SentenceTransformer

from services.database import pg_connection
from core.demo_responses import get_demo_scam_response

logger = logging.getLogger("surakshanet.scam_agent")

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

GROQ_API_KEY:   str  = os.environ["GROQ_API_KEY"]
DEMO_MOCK_MODE: bool = os.getenv("DEMO_MOCK_MODE", "false").lower() == "true"

# Groq model routing — Phase 2 uses the highest-precision 120B model
GROQ_MODEL: str       = "openai/gpt-oss-120b"
GROQ_TIMEOUT: float   = 30.0   # seconds before falling back
GROQ_MAX_TOKENS: int  = 1024
GROQ_TEMPERATURE: float = 0.1  # fixed at 0.1 — balanced between determinism and nuance

# Embedding model — runs on CPU inside the container, zero API cost
EMBED_MODEL_NAME: str = "all-MiniLM-L6-v2"
EMBED_DIMENSION:  int = 384
RAG_TOP_K:        int = 3     # top-N similar scam examples to inject as context

# Input guard — truncate runaway inputs before sending to the model
MAX_INPUT_CHARS: int = 4_000


# ─────────────────────────────────────────────────────────────────────────────
# Token Trimming & Normalization (Production Enhancement #1)
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_input(text: str) -> str:
    """
    Strip excessive whitespace, normalize unicode, and clamp input text to
    safe character limits BEFORE running the CPU embedding.
    Prevents memory leaks from runaway inputs and improves embedding quality.
    """
    # Collapse runs of whitespace (tabs, multiple spaces, weird unicode spaces)
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse 3+ consecutive newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip leading/trailing
    text = text.strip()
    # Hard clamp
    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS] + "\n[... truncated]"
    return text

# ─────────────────────────────────────────────────────────────────────────────
# Lazy-loaded singletons
# ─────────────────────────────────────────────────────────────────────────────

_groq_client:   Optional[AsyncGroq]           = None
_embed_model:   Optional[SentenceTransformer] = None


def _get_groq_client() -> AsyncGroq:
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncGroq(api_key=GROQ_API_KEY, timeout=GROQ_TIMEOUT)
        logger.info("Groq async client initialised (model=%s)", GROQ_MODEL)
    return _groq_client


def _get_embed_model() -> SentenceTransformer:
    """Load the embedding model once; reuse across all requests."""
    global _embed_model
    if _embed_model is None:
        logger.info("Loading sentence-transformer: %s …", EMBED_MODEL_NAME)
        _embed_model = SentenceTransformer(EMBED_MODEL_NAME)
        logger.info("Embedding model ready.")
    return _embed_model


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Schema — ScamAnalysisResult
# ─────────────────────────────────────────────────────────────────────────────

class RAGMatch(BaseModel):
    """One retrieved scam example used as RAG context."""
    category:   str
    similarity: float = Field(ge=0.0, le=1.0)
    excerpt:    str


class ScamAnalysisResult(BaseModel):
    """
    Canonical output contract for the scam analysis pipeline.
    This schema is shared with the FastAPI route layer and the frontend.
    """

    # ── Core verdict ─────────────────────────────────────────────────────────
    risk_score:  int   = Field(description="0 (safe) to 100 (certain scam)")
    category:    str   = Field(description="Scam type slug, e.g. 'digital_arrest'")
    confidence:  float = Field(ge=0.0, le=1.0)
    verdict:     str   = Field(description="SCAM | LIKELY_SCAM | UNCERTAIN | SAFE")

    # ── Psychological analysis ────────────────────────────────────────────────
    manipulation_tactics: list[str] = Field(
        default_factory=list,
        description="e.g. urgency, authority_impersonation, isolation, fear_induction",
    )
    red_flags: list[str] = Field(
        default_factory=list,
        description="Specific evidence phrases extracted from the input text",
    )

    # ── Human-readable explanations (bilingual) ───────────────────────────────
    explanation:    str = Field(description="Plain English explanation for the citizen")
    explanation_hi: str = Field(default="", description="Hindi translation of explanation")

    # ── Action guidance ───────────────────────────────────────────────────────
    recommended_actions: list[str] = Field(default_factory=list)

    # ── Pipeline metadata ─────────────────────────────────────────────────────
    rag_matches_used:   list[RAGMatch] = Field(default_factory=list)
    model_used:         str            = Field(default=GROQ_MODEL)
    processing_time_ms: float          = Field(default=0.0)

    @field_validator("risk_score")
    @classmethod
    def clamp_risk_score(cls, v: int) -> int:
        return max(0, min(100, v))

    @field_validator("verdict")
    @classmethod
    def normalise_verdict(cls, v: str) -> str:
        v = v.upper().strip()
        valid = {"SCAM", "LIKELY_SCAM", "UNCERTAIN", "SAFE"}
        return v if v in valid else "UNCERTAIN"

    @field_validator("category")
    @classmethod
    def slugify_category(cls, v: str) -> str:
        # Normalise to snake_case slug; strip spaces and special chars
        return re.sub(r"[^a-z0-9_]", "_", v.lower().strip()).strip("_")

    @model_validator(mode="after")
    def infer_verdict_from_score(self) -> "ScamAnalysisResult":
        """Ensure verdict is consistent with risk_score when model omits it."""
        if self.verdict == "UNCERTAIN":
            if self.risk_score >= 80:
                self.verdict = "SCAM"
            elif self.risk_score >= 50:
                self.verdict = "LIKELY_SCAM"
            elif self.risk_score <= 15:
                self.verdict = "SAFE"
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Embed user input
# ─────────────────────────────────────────────────────────────────────────────

def _embed_text(text: str) -> list[float]:
    """
    Synchronous embedding call wrapped for use in the async pipeline.
    sentence_transformers is CPU-bound; runs in ~20–40 ms on the free tier.
    """
    model = _get_embed_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Vector similarity search against known_scams (pgvector <=>)
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_rag_context(embedding: list[float], top_k: int = RAG_TOP_K) -> list[dict]:
    """
    Query Supabase known_scams table for the top_k most similar historical scam
    examples using pgvector cosine-distance operator (<=>).

    Advanced RAG Filtering (Production Enhancement #3):
    Ensures the top K matches are from DISTINCT categories, giving the LLM
    better comparative context across different scam types.

    Returns a list of dicts: [{ category, raw_text, risk_score, similarity }, ...]
    """
    vec_literal = "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"

    # Pull more candidates than needed so we can deduplicate by category
    fetch_limit = top_k * 4

    query = """
        SELECT DISTINCT ON (category)
            category,
            raw_text,
            risk_score,
            ROUND((1 - (embedding <=> $1::vector))::numeric, 4) AS similarity
        FROM (
            SELECT category, raw_text, risk_score, embedding
            FROM known_scams
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> $1::vector
            LIMIT $2
        ) AS candidates
        ORDER BY category, similarity DESC
    """
    try:
        async with pg_connection() as conn:
            rows = await conn.fetch(query, vec_literal, fetch_limit)
    except Exception:
        # Fallback: simpler query without DISTINCT ON if Supabase doesn't support it
        fallback_query = """
            SELECT
                category,
                raw_text,
                risk_score,
                ROUND((1 - (embedding <=> $1::vector))::numeric, 4) AS similarity
            FROM known_scams
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> $1::vector
            LIMIT $2
        """
        async with pg_connection() as conn:
            rows = await conn.fetch(fallback_query, vec_literal, top_k)

    # Deduplicate by category client-side as final safety net
    seen_categories: set[str] = set()
    results: list[dict] = []
    for row in sorted(rows, key=lambda r: -float(r["similarity"])):
        cat = row["category"]
        if cat in seen_categories:
            continue
        seen_categories.add(cat)
        results.append({
            "category":   cat,
            "raw_text":   row["raw_text"],
            "risk_score": row["risk_score"],
            "similarity": float(row["similarity"]),
        })
        if len(results) >= top_k:
            break

    logger.debug("RAG: retrieved %d distinct-category examples (top similarity=%.3f)",
                 len(results), results[0]["similarity"] if results else 0)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — System prompt construction
# ─────────────────────────────────────────────────────────────────────────────

_SCAM_CATEGORY_TAXONOMY = """
INDIAN CYBERCRIME CATEGORY TAXONOMY:
- digital_arrest        : Impersonation of CBI/ED/Police/Customs via video/audio call; false arrest threats
- kyc_phishing          : Fake bank/telecom KYC deadline; APK malware download; OTP harvesting
- upi_collect_fraud     : Fake UPI collect requests framed as prize/refund/lottery receipts
- investment_scam       : Fake stock tips, crypto platforms, or "doubling" schemes
- romance_scam          : Long-term emotional manipulation leading to financial extraction
- job_offer_scam        : Fake WFH/data-entry jobs with advance payment demand
- loan_app_fraud        : Instant loan apps that harvest contacts for blackmail
- sim_swap_fraud        : Fraudster ports victim's SIM to intercept OTPs
- courier_scam          : Fake customs/courier parcel with contraband; extortion demand
- lottery_prize_scam    : Unsolicited prize notification requiring processing fee
- tech_support_scam     : Fake virus alert; remote-access tool installation
- safe                  : Legitimate message, no fraud indicators detected
- unknown_suspicious    : Suspicious but does not match a specific category
"""

_MANIPULATION_TACTICS_GLOSSARY = """
PSYCHOLOGICAL MANIPULATION TACTICS TO DETECT:
- urgency                   : Artificial deadline (24 hours, "act now", "immediately")
- authority_impersonation   : Fake official, government agency, or executive identity
- fear_induction            : Threat of arrest, legal action, account freeze, blackmail
- isolation                 : Instruction to not tell family/friends/bank
- false_reward              : Fictitious prize, lottery win, or unexpected windfall
- social_proof              : "Others are already benefiting"; herd pressure
- reciprocity               : Small free gift before large financial ask
- scarcity                  : Limited slots, "only for you", expiring offer
- trust_building            : Extended rapport before the actual ask (romance/job scams)
- technical_confusion       : Jargon overload to bypass critical thinking
"""


def _build_system_prompt(rag_examples: list[dict]) -> str:
    """
    Construct the precision-engineered system prompt injecting RAG context.
    The prompt enforces strict JSON output with no prose wrapper.
    """

    # Format RAG examples as numbered reference cases
    rag_section_lines = []
    for i, ex in enumerate(rag_examples, start=1):
        rag_section_lines.append(
            f"  [{i}] Category: {ex['category']} | Similarity: {ex['similarity']:.2f} | "
            f"Baseline Risk: {ex['risk_score']}/100\n"
            f"      Sample: \"{ex['raw_text'][:200]}\""
        )
    rag_section = "\n".join(rag_section_lines) if rag_section_lines else "  [No matches found]"

    return f"""You are SurakshaNet's cybercrime forensic analyst AI, specialising in Indian financial fraud. You help citizens identify genuine scams — but you must be accurate, not paranoid.

{_SCAM_CATEGORY_TAXONOMY}

{_MANIPULATION_TACTICS_GLOSSARY}

RETRIEVED REFERENCE CASES (from known Indian cybercrime corpus):
{rag_section}

DO NOT FLAG THESE AS SCAMS (they are legitimate):
- Standard promotional marketing, discount offers, sale announcements from known brands
- Routine banking alerts: transaction confirmations, balance updates, statement notices
- OTP messages that the user themselves triggered (login, payment, registration)
- Delivery tracking updates from courier services (Amazon, Flipkart, Delhivery, etc.)
- Appointment reminders, bill due notices, subscription renewals
- Casual urgency in normal business context ("offer ends today", "limited stock")
- Personal messages between friends, family, or colleagues
- Government service notifications (Aadhaar update, IRCTC booking, EPFO alerts)
ONLY FLAG if there is CLEAR MALICIOUS INTENT such as:
  - Demanding money transfer to an unknown account under threat or false pretext
  - Threatening legal action, arrest, or account suspension to extract money
  - Requesting OTPs, passwords, or credentials they should not need
  - Impersonating a government officer/police to extort payment
  - Promising impossible returns to lure investment

RISK SCORE CALIBRATION:
  0–15:  Safe — routine banking, marketing, personal chat, delivery updates
  16–35: Mildly suspicious — unusual request but no clear malicious intent
  36–55: Moderately suspicious — multiple red flags but ambiguous
  56–75: Highly suspicious — strong indicators of malicious intent
  76–100: Definite scam — clear criminal pattern (money demand + threat/impersonation)

VERDICT MAPPING (strictly follow this):
  SAFE        = risk_score 0–25
  UNCERTAIN   = risk_score 26–50
  LIKELY_SCAM = risk_score 51–75
  SCAM        = risk_score 76–100

CRITICAL OUTPUT RULES:
- Respond with ONLY a single valid JSON object. No markdown fences, no prose.
- manipulation_tactics and red_flags MUST be empty arrays [] for safe/uncertain messages.
- The JSON must exactly match this schema:

{{
  "risk_score": <integer 0-100>,
  "category": "<slug from taxonomy>",
  "confidence": <float 0.0-1.0>,
  "verdict": "<SCAM|LIKELY_SCAM|UNCERTAIN|SAFE>",
  "manipulation_tactics": ["<tactic_slug>", ...],
  "red_flags": ["<specific evidence phrase>", ...],
  "explanation": "<plain English explanation>",
  "explanation_hi": "<Hindi explanation>",
  "recommended_actions": ["<action 1>", ...]
}}"""


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Groq 120B inference call
# ─────────────────────────────────────────────────────────────────────────────

async def _call_groq(system_prompt: str, user_text: str) -> str:
    """
    Call Groq openai/gpt-oss-120b and return the raw JSON string.
    Raises on API errors — caller handles fallback.
    """
    client = _get_groq_client()

    response = await client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": f"Analyze this text for scam indicators:\n\n{user_text}"},
        ],
        temperature=GROQ_TEMPERATURE,
        max_tokens=GROQ_MAX_TOKENS,
        response_format={"type": "json_object"},   # enforce JSON mode
        stream=False,
    )

    raw = response.choices[0].message.content or ""
    logger.debug(
        "Groq response received  tokens_used=%d  finish_reason=%s",
        response.usage.total_tokens if response.usage else -1,
        response.choices[0].finish_reason,
    )
    return raw


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Parse and validate Groq output
# ─────────────────────────────────────────────────────────────────────────────

def _parse_groq_response(raw: str, rag_matches: list[dict], elapsed_ms: float) -> ScamAnalysisResult:
    """
    Parse raw JSON string from Groq into a validated ScamAnalysisResult.

    Hardened JSON Repair Layer (Production Enhancement #2):
      - Strips markdown fences (```json ... ```)
      - Removes trailing commas before } or ]
      - Extracts outermost JSON object even with surrounding prose
      - Handles partial/malformed keys gracefully via Pydantic defaults
    """
    cleaned = raw.strip()

    # Step 1: Strip markdown fences if model ignored no-fence instruction
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    # Step 2: Find the outermost JSON object if there's surrounding prose
    obj_match = re.search(r"\{[\s\S]+\}", cleaned)
    if obj_match:
        cleaned = obj_match.group(0)

    # Step 3: Remove trailing commas (common LLM mistake)
    # e.g., {"a": 1, "b": 2,} → {"a": 1, "b": 2}
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

    # Step 4: Remove single-line // comments that some models inject
    cleaned = re.sub(r"//[^\n]*", "", cleaned)

    data: dict[str, Any] = json.loads(cleaned)  # raises json.JSONDecodeError on bad output

    # Attach pipeline metadata
    data["rag_matches_used"] = [
        RAGMatch(
            category=m["category"],
            similarity=m["similarity"],
            excerpt=m["raw_text"][:120] + ("…" if len(m["raw_text"]) > 120 else ""),
        )
        for m in rag_matches
    ]
    data["model_used"]         = GROQ_MODEL
    data["processing_time_ms"] = round(elapsed_ms, 2)

    # Ensure required fields have safe defaults if model omitted them
    data.setdefault("manipulation_tactics", [])
    data.setdefault("red_flags", [])
    data.setdefault("recommended_actions", [])
    data.setdefault("explanation_hi", "")
    data.setdefault("explanation", "Analysis complete.")

    return ScamAnalysisResult(**data)


# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — Persist incident to Supabase
# ─────────────────────────────────────────────────────────────────────────────

async def _persist_incident(
    session_id: str,
    raw_input: str,
    result: ScamAnalysisResult,
    top_match_category: Optional[str] = None,
) -> None:
    """
    Write the analysis result to incident_reports for audit and analytics.
    Non-fatal — a persistence failure must never surface to the end user.
    """
    try:
        insert_sql = """
            INSERT INTO incident_reports (
                session_id, input_type, raw_input,
                risk_score, verdict,
                explanation_en, explanation_hi,
                created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, now())
        """
        async with pg_connection() as conn:
            await conn.execute(
                insert_sql,
                uuid.UUID(session_id),
                "text",
                raw_input[:2000],            # cap stored input to 2 KB
                result.risk_score,
                result.verdict,
                result.explanation,
                result.explanation_hi,
            )
        logger.debug("Incident persisted  session_id=%s  verdict=%s", session_id, result.verdict)
    except Exception as exc:
        logger.warning("Incident persistence failed (non-fatal): %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Public API — analyse_text()
# ─────────────────────────────────────────────────────────────────────────────

async def analyse_text(
    text: str,
    session_id: Optional[str] = None,
    *,
    skip_persist: bool = False,
) -> ScamAnalysisResult:
    """
    Full scam analysis pipeline for a text input (typed message or audio transcript).

    Parameters
    ----------
    text         : Raw user input — SMS, WhatsApp message, call transcript, etc.
    session_id   : UUID string linking this request to a browser session for
                   audit trail. Auto-generated if not provided.
    skip_persist : Set True in unit tests to avoid DB writes.

    Returns
    -------
    ScamAnalysisResult — always returns something; falls back to demo data on error.

    Never raises — all exceptions are caught, logged, and converted to either a
    fallback response (DEMO_MOCK_MODE) or a safe UNCERTAIN result.
    """
    session_id = session_id or str(uuid.uuid4())
    t_start    = time.monotonic()

    # ── Input sanitation ────────────────────────────────────────────────────
    text = text.strip()
    if not text:
        return ScamAnalysisResult(
            risk_score=0,
            category="safe",
            confidence=1.0,
            verdict="SAFE",
            explanation="No input text provided.",
            explanation_hi="कोई इनपुट टेक्स्ट नहीं दिया गया।",
        )

    # Token trimming & normalization — collapse whitespace, clamp length
    text = _normalize_input(text)

    # ── Demo / mock shortcut ────────────────────────────────────────────────
    if DEMO_MOCK_MODE:
        logger.info("DEMO_MOCK_MODE active — returning canned response.")
        hint = _guess_category_hint(text)
        demo = get_demo_scam_response(hint)
        demo["processing_time_ms"] = round((time.monotonic() - t_start) * 1000, 2)
        return ScamAnalysisResult(**demo)

    # ── Live pipeline ───────────────────────────────────────────────────────
    rag_matches: list[dict] = []

    try:
        # Step 1: Embed (CPU — run in threadpool to avoid blocking event loop)
        loop = asyncio.get_running_loop()
        embedding: list[float] = await loop.run_in_executor(None, _embed_text, text)

        # Step 2: Vector similarity search
        try:
            rag_matches = await _fetch_rag_context(embedding)
        except Exception as db_exc:
            # RAG failure is non-fatal — continue with zero context
            logger.warning("RAG fetch failed (continuing without context): %s", db_exc)
            rag_matches = []

        # Step 3: Build system prompt with RAG context
        system_prompt = _build_system_prompt(rag_matches)

        # Step 4: Groq inference
        raw_response = await _call_groq(system_prompt, text)

        # Step 5: Parse + validate
        elapsed_ms = (time.monotonic() - t_start) * 1000
        result = _parse_groq_response(raw_response, rag_matches, elapsed_ms)

        # Step 6: Persist (non-blocking — fire and forget)
        if not skip_persist:
            top_cat = rag_matches[0]["category"] if rag_matches else None
            asyncio.create_task(_persist_incident(session_id, text, result, top_cat))

        logger.info(
            "ScamAnalysis complete  session=%s  verdict=%s  risk=%d  "
            "category=%s  elapsed=%.0f ms",
            session_id, result.verdict, result.risk_score,
            result.category, result.processing_time_ms,
        )
        return result

    except (APITimeoutError, asyncio.TimeoutError) as exc:
        logger.error("Groq timeout  session=%s: %s", session_id, exc)
        return _fallback_result(text, rag_matches, t_start, reason="groq_timeout")

    except RateLimitError as exc:
        logger.error("Groq rate limit  session=%s: %s", session_id, exc)
        return _fallback_result(text, rag_matches, t_start, reason="groq_rate_limit")

    except APIStatusError as exc:
        logger.error("Groq API error %d  session=%s: %s", exc.status_code, session_id, exc)
        return _fallback_result(text, rag_matches, t_start, reason=f"groq_api_{exc.status_code}")

    except json.JSONDecodeError as exc:
        logger.error("JSON parse error  session=%s: %s", session_id, exc)
        return _fallback_result(text, rag_matches, t_start, reason="json_parse_error")

    except Exception as exc:
        logger.exception("Unexpected error in analyse_text  session=%s: %s", session_id, exc)
        return _fallback_result(text, rag_matches, t_start, reason="unexpected_error")


# ─────────────────────────────────────────────────────────────────────────────
# Fallback helpers
# ─────────────────────────────────────────────────────────────────────────────

def _guess_category_hint(text: str) -> str:
    """
    Keyword-based category hint for demo mode and fallback construction.
    Returns a slug fragment that get_demo_scam_response() can match on.
    """
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["cbi", "ed", "customs", "arrest", "narcotics", "aadhaar linked", "digital custody"]):
        return "digital_arrest"
    if any(kw in text_lower for kw in ["kyc", "otp", "apk", "blocked", "bank account", "update your"]):
        return "kyc_phishing"
    if any(kw in text_lower for kw in ["upi", "collect", "prize", "lottery", "refund", "₹", "paytm", "gpay"]):
        return "upi_collect_fraud"
    if any(kw in text_lower for kw in ["invest", "stock", "crypto", "return", "profit", "double"]):
        return "investment_scam"
    if any(kw in text_lower for kw in ["job", "work from home", "wfh", "salary", "advance"]):
        return "job_offer_scam"
    return "default"


def _fallback_result(
    text: str,
    rag_matches: list[dict],
    t_start: float,
    reason: str = "unknown",
) -> ScamAnalysisResult:
    """
    Construct a safe fallback result when the live pipeline fails.
    Uses demo data if DEMO_MOCK_MODE is on, otherwise returns a conservative
    LIKELY_SCAM result so the user is protected rather than left unwarned.
    """
    elapsed_ms = round((time.monotonic() - t_start) * 1000, 2)
    logger.warning("Falling back to safe response  reason=%s  elapsed=%.0f ms", reason, elapsed_ms)

    if DEMO_MOCK_MODE:
        hint = _guess_category_hint(text)
        demo = get_demo_scam_response(hint)
        demo["processing_time_ms"] = elapsed_ms
        demo["model_used"] = f"demo_fallback:{reason}"
        return ScamAnalysisResult(**demo)

    # Production fallback: conservative LIKELY_SCAM to protect the user
    return ScamAnalysisResult(
        risk_score=65,
        category="unknown_suspicious",
        confidence=0.50,
        verdict="LIKELY_SCAM",
        manipulation_tactics=[],
        red_flags=["Analysis temporarily unavailable — treat with caution"],
        explanation=(
            "Our analysis service is temporarily unavailable. "
            "As a precaution, please do not transfer money or share personal "
            "details. Call Cyber Crime Helpline 1930 if you feel at risk."
        ),
        explanation_hi=(
            "विश्लेषण सेवा अस्थायी रूप से उपलब्ध नहीं है। "
            "सावधानी बरतें और 1930 पर कॉल करें।"
        ),
        recommended_actions=[
            "Do not transfer money or share OTPs.",
            "Call Cyber Crime Helpline 1930 immediately if you feel at risk.",
            "Try again in a few minutes when the service recovers.",
        ],
        rag_matches_used=[
            RAGMatch(
                category=m["category"],
                similarity=m["similarity"],
                excerpt=m["raw_text"][:120],
            )
            for m in rag_matches
        ],
        model_used=f"fallback:{reason}",
        processing_time_ms=elapsed_ms,
    )
