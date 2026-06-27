"""
backend/agents/counterfeit_agent.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SurakshaNet AI — Bank-Teller Counterfeit Detection Agent
Uses Pillow (PIL) for image processing — no OpenCV/libGL system dependencies.

Pipeline:
  1. Decode image bytes via Pillow — no system libs needed.
  2. Basic image analysis: contrast, brightness variance, edge approximation.
  3. Encode image as base64 and call Groq vision model for forensic analysis.
  4. Parse and validate the Groq response against the CounterfeitResult schema.
  5. Persist the scan result to Supabase counterfeit_scans for branch analytics.
  6. On any failure: DEMO_MOCK_MODE → canned fixture; production → conservative SUSPECT.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import math
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from groq import AsyncGroq, APITimeoutError, RateLimitError, APIStatusError
from PIL import Image, ImageFilter, ImageOps
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from services.database import pg_connection
from core.demo_responses import get_demo_counterfeit_response

logger = logging.getLogger("surakshanet.counterfeit_agent")

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

GROQ_API_KEY:   str  = os.environ["GROQ_API_KEY"]
DEMO_MOCK_MODE: bool = os.getenv("DEMO_MOCK_MODE", "false").lower() == "true"

GROQ_VISION_MODEL: str   = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_TIMEOUT:      float = 45.0
GROQ_MAX_TOKENS:   int   = 1024
GROQ_TEMPERATURE:  float = 0.05

MAX_IMAGE_BYTES:  int = 15 * 1024 * 1024  # 15 MB
MAX_DIMENSION_PX: int = 2048              # downscale if larger

# ─────────────────────────────────────────────────────────────────────────────
# Lazy singleton
# ─────────────────────────────────────────────────────────────────────────────

_groq_client: Optional[AsyncGroq] = None


def _get_groq_client() -> AsyncGroq:
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncGroq(api_key=GROQ_API_KEY, timeout=GROQ_TIMEOUT)
        logger.info("Groq vision client initialised (model=%s)", GROQ_VISION_MODEL)
    return _groq_client


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas
# ─────────────────────────────────────────────────────────────────────────────

class OpenCVMetrics(BaseModel):
    """Image analysis metrics — stored in Supabase JSONB."""
    clahe_contrast_score:  float = Field(ge=0.0, le=1.0)
    fft_watermark_opacity: float = Field(ge=0.0, le=1.0)
    laplacian_variance:    float = Field(ge=0.0)
    sobel_edge_density:    float = Field(ge=0.0, le=1.0)
    bleed_line_count:      int   = Field(ge=0)


class CounterfeitResult(BaseModel):
    """Canonical output contract for the counterfeit detection pipeline."""

    model_config = ConfigDict(protected_namespaces=())

    verdict:      str   = Field(description="GENUINE | SUSPECT | COUNTERFEIT")
    final_score:  int   = Field(description="0 (counterfeit) to 100 (genuine)")
    confidence:   float = Field(ge=0.0, le=1.0)
    denomination: int   = Field(default=0, description="100/200/500/2000")

    features_passed: list[str] = Field(default_factory=list)
    features_failed: list[str] = Field(default_factory=list)

    opencv_metrics: OpenCVMetrics

    explanation:         str       = Field(description="Teller-facing verdict explanation")
    recommended_actions: list[str] = Field(default_factory=list)

    model_used:         str   = Field(default=GROQ_VISION_MODEL)
    processing_time_ms: float = Field(default=0.0)

    @field_validator("verdict")
    @classmethod
    def normalise_verdict(cls, v: str) -> str:
        v = v.upper().strip()
        return v if v in {"GENUINE", "SUSPECT", "COUNTERFEIT"} else "SUSPECT"

    @field_validator("final_score")
    @classmethod
    def clamp_score(cls, v: int) -> int:
        return max(0, min(100, v))

    @model_validator(mode="after")
    def sync_verdict_score(self) -> "CounterfeitResult":
        if self.final_score >= 85 and self.verdict == "COUNTERFEIT":
            self.verdict = "SUSPECT"
        if self.final_score <= 15 and self.verdict == "GENUINE":
            self.verdict = "SUSPECT"
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Internal dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class _ImgAnalysis:
    enhanced_jpg_bytes: bytes
    metrics:            OpenCVMetrics
    pre_score:          int
    features_passed:    list[str] = field(default_factory=list)
    features_failed:    list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Pillow-based image analysis (replaces OpenCV — no libGL needed)
# ─────────────────────────────────────────────────────────────────────────────

def _pillow_analyse(image_bytes: bytes) -> _ImgAnalysis:
    """
    Pure-Pillow image forensics pipeline.
    No cv2, no numpy, no system library dependencies.
    """
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError(f"Image too large: {len(image_bytes):,} bytes")

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # Downscale if needed
    w, h = img.size
    if max(w, h) > MAX_DIMENSION_PX:
        scale = MAX_DIMENSION_PX / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        w, h = img.size

    # ── Contrast score via histogram spread ──────────────────────────────────
    grey = ImageOps.grayscale(img)
    hist = grey.histogram()          # 256-bucket histogram
    total_px = w * h
    # Mean brightness
    mean_l = sum(i * hist[i] for i in range(256)) / total_px
    # Standard deviation of brightness → contrast proxy
    variance_l = sum(((i - mean_l) ** 2) * hist[i] for i in range(256)) / total_px
    std_l = math.sqrt(variance_l)
    contrast_score = min(1.0, std_l / 127.5)

    # ── FFT-proxy: high-frequency energy via edge filter ─────────────────────
    # Use PIL's FIND_EDGES filter as a simple frequency-domain proxy
    edges = grey.filter(ImageFilter.FIND_EDGES)
    edge_pixels = list(edges.getdata())
    edge_mean = sum(edge_pixels) / len(edge_pixels)
    fft_proxy = min(1.0, edge_mean / 80.0)   # normalise: 80 is typical genuine note

    # ── Laplacian-proxy: sharpness via unsharp mask response ─────────────────
    sharpened = grey.filter(ImageFilter.SHARPEN)
    sharp_pixels = list(sharpened.getdata())
    orig_pixels  = list(grey.getdata())
    diff_sq_sum  = sum((s - o) ** 2 for s, o in zip(sharp_pixels, orig_pixels))
    lap_proxy    = math.sqrt(diff_sq_sum / len(orig_pixels))  # RMS sharpness response

    # ── Edge density (sobel-proxy via FIND_EDGES) ─────────────────────────────
    active_edges = sum(1 for p in edge_pixels if p > 20)
    edge_density = active_edges / len(edge_pixels)

    # ── Bleed-line proxy: vertical edge count in left/right strips ─────────────
    strip_w  = max(1, int(w * 0.12))
    left  = edges.crop((0, 0, strip_w, h))
    right = edges.crop((w - strip_w, 0, w, h))
    left_px  = list(left.getdata())
    right_px = list(right.getdata())
    active_strip = sum(1 for p in left_px + right_px if p > 30)
    bleed_line_count = min(60, active_strip // max(1, h // 20))

    # ── CLAHE-equivalent: auto-contrast enhancement ────────────────────────────
    enhanced = ImageOps.autocontrast(img, cutoff=2)
    buf = io.BytesIO()
    enhanced.save(buf, format="JPEG", quality=88)
    enhanced_jpg_bytes = buf.getvalue()

    # ── Feature pass/fail ────────────────────────────────────────────────────
    features_passed: list[str] = []
    features_failed: list[str] = []

    if fft_proxy >= 0.30:
        features_passed.append("watermark_opacity")
    else:
        features_failed.append("watermark_opacity")

    if lap_proxy >= 5.0:
        features_passed.append("intaglio_sharpness")
    else:
        features_failed.append("intaglio_sharpness")

    if contrast_score >= 0.40:
        features_passed.append("scan_quality")
    else:
        features_failed.append("scan_quality")

    if bleed_line_count >= 8:
        features_passed.append("bleed_lines")
    else:
        features_failed.append("bleed_lines")

    if edge_density >= 0.10:
        features_passed.append("surface_complexity")
    else:
        features_failed.append("surface_complexity")

    # ── Pre-score (0-100) ─────────────────────────────────────────────────────
    score = 0
    if "watermark_opacity"  in features_passed: score += 35
    elif fft_proxy >= 0.18:                      score += 15
    if "intaglio_sharpness" in features_passed: score += 30
    elif lap_proxy >= 3.0:                       score += 15
    if "bleed_lines"        in features_passed: score += 15
    if "surface_complexity" in features_passed: score += 12
    if "scan_quality"       in features_passed: score +=  8

    metrics = OpenCVMetrics(
        clahe_contrast_score  = round(contrast_score, 4),
        fft_watermark_opacity = round(fft_proxy, 4),
        laplacian_variance    = round(lap_proxy, 2),
        sobel_edge_density    = round(edge_density, 4),
        bleed_line_count      = bleed_line_count,
    )
    logger.debug(
        "Pillow analysis: pre_score=%d contrast=%.3f fft=%.3f lap=%.2f lines=%d",
        score, contrast_score, fft_proxy, lap_proxy, bleed_line_count,
    )
    return _ImgAnalysis(
        enhanced_jpg_bytes=enhanced_jpg_bytes,
        metrics=metrics,
        pre_score=score,
        features_passed=features_passed,
        features_failed=features_failed,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Vision prompt
# ─────────────────────────────────────────────────────────────────────────────

_RBI_SECURITY_FEATURES = """
GENUINE RBI CURRENCY NOTE SECURITY FEATURES:
1. WATERMARK       : Gandhi portrait watermark visible when held to light; embedded in paper.
2. SECURITY THREAD : Windowed demetallised magnetic thread reading 'भारत' / 'RBI'.
3. INTAGLIO PRINT  : Governor's signature, guarantee text, Ashoka pillar are raised to touch.
4. LATENT IMAGE    : Denominational numeral visible at an angle.
5. MICROLETTERING  : 'RBI' and numeral visible under magnification below Gandhi portrait.
6. COLOUR SHIFT    : Numeral panel shifts green→blue when tilted (₹500, ₹2000).
7. BLEED LINES     : Seven angular bleed lines at left and right edges.
"""


def _build_vision_prompt(analysis: _ImgAnalysis) -> str:
    m = analysis.metrics
    passed_str = ", ".join(analysis.features_passed) or "none"
    failed_str = ", ".join(analysis.features_failed) or "none"

    return f"""You are SurakshaNet's bank-teller forensic vision AI. Determine if this currency note is GENUINE, SUSPECT, or COUNTERFEIT.

{_RBI_SECURITY_FEATURES}

PRE-COMPUTED IMAGE METRICS:
  • Contrast score    : {m.clahe_contrast_score:.4f}
  • Edge/FFT proxy    : {m.fft_watermark_opacity:.4f}
  • Sharpness proxy   : {m.laplacian_variance:.2f}
  • Edge density      : {m.sobel_edge_density:.4f}
  • Bleed line count  : {m.bleed_line_count}
  • Pre-score         : {analysis.pre_score}/100

FEATURE REPORT:
  ✓ PASSED: {passed_str}
  ✗ FAILED: {failed_str}

CALIBRATION — phone photos will have blur, uneven lighting, slight distortion. Do NOT fail for these.
Reserve COUNTERFEIT only when multiple primary features (Gandhi portrait, security thread, denomination numerals) are clearly absent or fake.

VERDICT GUIDE:
  GENUINE     : final_score 65–100
  SUSPECT     : final_score 35–64
  COUNTERFEIT : final_score 0–34

OUTPUT: Respond ONLY with valid JSON, no markdown.

{{
  "verdict": "<GENUINE|SUSPECT|COUNTERFEIT>",
  "final_score": <0-100>,
  "confidence": <0.0-1.0>,
  "denomination": <100|200|500|2000|0>,
  "features_passed": ["..."],
  "features_failed": ["..."],
  "explanation": "<teller-facing explanation>",
  "recommended_actions": ["..."]
}}"""


# ─────────────────────────────────────────────────────────────────────────────
# Groq vision call
# ─────────────────────────────────────────────────────────────────────────────

async def _call_groq_vision(system_prompt: str, jpg_bytes: bytes) -> str:
    client = _get_groq_client()
    b64    = base64.b64encode(jpg_bytes).decode("utf-8")
    uri    = f"data:image/jpeg;base64,{b64}"

    response = await client.chat.completions.create(
        model=GROQ_VISION_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": uri, "detail": "high"}},
                    {"type": "text", "text": "Perform forensic analysis. Return only the JSON verdict."},
                ],
            },
        ],
        temperature=GROQ_TEMPERATURE,
        max_tokens=GROQ_MAX_TOKENS,
    )
    return response.choices[0].message.content or ""


# ─────────────────────────────────────────────────────────────────────────────
# Parse Groq response
# ─────────────────────────────────────────────────────────────────────────────

def _parse_vision_response(
    raw: str,
    analysis: _ImgAnalysis,
    elapsed_ms: float,
) -> CounterfeitResult:
    cleaned = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    obj = re.search(r"\{[\s\S]+\}", cleaned)
    if obj:
        cleaned = obj.group(0)

    data: dict[str, Any] = json.loads(cleaned)

    llava_passed = set(data.get("features_passed", []))
    llava_failed = set(data.get("features_failed", []))
    cv_passed    = set(analysis.features_passed)
    cv_failed    = set(analysis.features_failed)

    merged_passed = list(llava_passed | (cv_passed - llava_failed))
    merged_failed = list(llava_failed | (cv_failed - llava_passed))
    merged_failed = [f for f in merged_failed if f not in merged_passed]

    data["features_passed"]    = merged_passed
    data["features_failed"]    = merged_failed
    data["opencv_metrics"]     = analysis.metrics
    data["model_used"]         = GROQ_VISION_MODEL
    data["processing_time_ms"] = round(elapsed_ms, 2)

    return CounterfeitResult(**data)


# ─────────────────────────────────────────────────────────────────────────────
# Persist to Supabase
# ─────────────────────────────────────────────────────────────────────────────

async def _persist_scan(
    scan_id: str,
    branch_code: Optional[str],
    result: CounterfeitResult,
) -> None:
    try:
        import json as _json
        sql = """
            INSERT INTO counterfeit_scans (
                id, branch_code, denomination, verdict,
                confidence, opencv_flags, llava_response, scanned_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, now())
        """
        async with pg_connection() as conn:
            await conn.execute(
                sql,
                uuid.UUID(scan_id),
                branch_code,
                result.denomination if result.denomination != 0 else None,
                result.verdict,
                result.confidence,
                _json.dumps(result.opencv_metrics.model_dump()),
                result.explanation[:500],
            )
        logger.debug("Scan persisted  id=%s  verdict=%s", scan_id, result.verdict)
    except Exception as exc:
        logger.warning("Scan persistence failed (non-fatal): %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Fallback helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fallback_result(
    analysis: Optional[_ImgAnalysis],
    t_start: float,
    reason: str = "unknown",
) -> CounterfeitResult:
    elapsed_ms = round((time.monotonic() - t_start) * 1000, 2)
    logger.warning("Counterfeit fallback  reason=%s  elapsed=%.0f ms", reason, elapsed_ms)

    empty_metrics = OpenCVMetrics(
        clahe_contrast_score=0.0,
        fft_watermark_opacity=0.0,
        laplacian_variance=0.0,
        sobel_edge_density=0.0,
        bleed_line_count=0,
    )

    if DEMO_MOCK_MODE:
        hint = "suspect"
        if analysis:
            hint = "genuine" if analysis.pre_score >= 75 else ("suspect" if analysis.pre_score >= 35 else "counterfeit")
        demo = get_demo_counterfeit_response(hint)
        demo["processing_time_ms"] = elapsed_ms
        demo["model_used"] = f"demo_fallback:{reason}"
        demo["opencv_metrics"] = analysis.metrics if analysis else empty_metrics
        return CounterfeitResult(**demo)

    return CounterfeitResult(
        verdict="SUSPECT",
        final_score=40,
        confidence=0.40,
        denomination=0,
        features_passed=analysis.features_passed if analysis else [],
        features_failed=analysis.features_failed if analysis else [],
        opencv_metrics=analysis.metrics if analysis else empty_metrics,
        explanation=(
            f"Automated verification temporarily unavailable (reason: {reason}). "
            "Flagged as SUSPECT by default. Please perform manual UV lamp verification."
        ),
        recommended_actions=[
            "Perform manual UV lamp and feel-based verification.",
            "Escalate to branch manager if uncertain.",
            "Do not return note to customer while pending.",
            "Retry the automated scan — service should recover shortly.",
        ],
        model_used=f"fallback:{reason}",
        processing_time_ms=elapsed_ms,
    )


def _build_analysis_only_result(analysis: _ImgAnalysis, t_start: float) -> CounterfeitResult:
    score = analysis.pre_score
    verdict, confidence = (
        ("GENUINE", 0.60) if score >= 75 else
        ("SUSPECT", 0.55) if score >= 35 else
        ("COUNTERFEIT", 0.65)
    )
    elapsed_ms = round((time.monotonic() - t_start) * 1000, 2)
    return CounterfeitResult(
        verdict=verdict,
        final_score=score,
        confidence=confidence,
        denomination=0,
        features_passed=analysis.features_passed,
        features_failed=analysis.features_failed,
        opencv_metrics=analysis.metrics,
        explanation=(
            f"Vision model unavailable — verdict based on image analysis only "
            f"(pre-score {score}/100). Manual UV lamp verification recommended."
        ),
        recommended_actions=[
            "Perform UV lamp verification to cross-check this result.",
            "Escalate to branch manager — full AI analysis was unavailable.",
        ],
        model_used="pillow_analysis_only",
        processing_time_ms=elapsed_ms,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def analyse_note(
    image_bytes: bytes,
    branch_code: Optional[str] = None,
    scan_id: Optional[str] = None,
    *,
    skip_persist: bool = False,
) -> CounterfeitResult:
    """
    Full counterfeit detection pipeline. Never raises — always returns a result.
    """
    scan_id = scan_id or str(uuid.uuid4())
    t_start = time.monotonic()
    analysis: Optional[_ImgAnalysis] = None

    if not image_bytes:
        return _fallback_result(None, t_start, reason="empty_image")

    if DEMO_MOCK_MODE:
        logger.info("DEMO_MOCK_MODE — returning canned response.")
        demo = get_demo_counterfeit_response("suspect")
        demo["processing_time_ms"] = round((time.monotonic() - t_start) * 1000, 2)
        return CounterfeitResult(**demo)

    try:
        # Image analysis (CPU-bound → thread pool)
        loop = asyncio.get_running_loop()
        analysis = await loop.run_in_executor(None, _pillow_analyse, image_bytes)

        logger.info(
            "Image analysis complete  scan=%s  pre_score=%d",
            scan_id, analysis.pre_score,
        )

        system_prompt = _build_vision_prompt(analysis)
        raw_response  = await _call_groq_vision(system_prompt, analysis.enhanced_jpg_bytes)

        elapsed_ms = (time.monotonic() - t_start) * 1000
        result = _parse_vision_response(raw_response, analysis, elapsed_ms)

        if not skip_persist:
            asyncio.create_task(_persist_scan(scan_id, branch_code, result))

        logger.info(
            "CounterfeitAnalysis done  scan=%s  verdict=%s  score=%d  elapsed=%.0f ms",
            scan_id, result.verdict, result.final_score, result.processing_time_ms,
        )
        return result

    except ValueError as exc:
        logger.error("Invalid image  scan=%s: %s", scan_id, exc)
        return _fallback_result(analysis, t_start, reason=f"invalid_image:{exc}")

    except (APITimeoutError, asyncio.TimeoutError):
        logger.error("Groq vision timeout  scan=%s", scan_id)
        return _fallback_result(analysis, t_start, reason="groq_timeout")

    except RateLimitError:
        logger.error("Groq rate limit  scan=%s", scan_id)
        return _fallback_result(analysis, t_start, reason="groq_rate_limit")

    except APIStatusError as exc:
        logger.error("Groq API error %d  scan=%s", exc.status_code, scan_id)
        return _fallback_result(analysis, t_start, reason=f"groq_api_{exc.status_code}")

    except json.JSONDecodeError:
        logger.error("JSON parse error  scan=%s", scan_id)
        if analysis:
            return _build_analysis_only_result(analysis, t_start)
        return _fallback_result(None, t_start, reason="json_parse_error")

    except Exception as exc:
        logger.exception("Unexpected error  scan=%s: %s", scan_id, exc)
        return _fallback_result(analysis, t_start, reason="unexpected_error")
