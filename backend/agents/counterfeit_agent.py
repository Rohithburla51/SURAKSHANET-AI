"""
backend/agents/counterfeit_agent.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SurakshaNet AI — Phase 2: Bank-Teller Counterfeit Detection Agent
Model: Claude Sonnet 4.6 (1.3x) — Heavy OpenCV math + LLaVA vision task

Pipeline (per request):
  1. Decode raw image bytes → OpenCV BGR array; reject corrupt/oversized inputs.
  2. CLAHE contrast enhancement on L-channel (LAB colour space) to normalise
     scan quality variance across different phone cameras and flatbed scanners.
  3. FFT watermark opacity analysis — measures frequency-domain energy in the
     mid-band region where the RBI Gandhi watermark embeds its spatial signature.
  4. Laplacian variance for intaglio print sharpness — genuine notes have
     sharply embossed ink; counterfeits printed on inkjet/laser have low variance.
  5. Sobel edge density for bleed-line geometry — counts dominant vertical edges
     to verify the correct number of security bleed lines per denomination.
  6. Aggregate the OpenCV metrics into a feature-pass/fail report and a 0-100
     pre-score that primes the vision model's reasoning.
  7. Encode the CLAHE-enhanced image as base64 and call Groq llama-3.2-90b-vision-preview
     with a forensic system prompt that includes the pre-computed metrics as context.
  8. Parse and validate the Groq response against the CounterfeitResult Pydantic schema.
  9. Persist the scan result to Supabase counterfeit_scans for branch analytics.
  10. On any failure: DEMO_MOCK_MODE → canned fixture; production → conservative
      SUSPECT verdict so tellers never silently accept a bad note.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

import cv2
import numpy as np
from groq import AsyncGroq, APITimeoutError, RateLimitError, APIStatusError
from pydantic import BaseModel, Field, field_validator, model_validator

from services.database import pg_connection
from core.demo_responses import get_demo_counterfeit_response

logger = logging.getLogger("surakshanet.counterfeit_agent")

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

GROQ_API_KEY:    str   = os.environ["GROQ_API_KEY"]
DEMO_MOCK_MODE:  bool  = os.getenv("DEMO_MOCK_MODE", "false").lower() == "true"

GROQ_VISION_MODEL:   str   = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_TIMEOUT:        float = 45.0   # vision inference is slower than text
GROQ_MAX_TOKENS:     int   = 1024
GROQ_TEMPERATURE:    float = 0.05   # near-zero — forensic verdicts must be deterministic

# Image intake limits
MAX_IMAGE_BYTES:   int = 15 * 1024 * 1024   # 15 MB hard cap
MAX_DIMENSION_PX:  int = 4096               # resize to this if larger

# CLAHE parameters (Contrast Limited Adaptive Histogram Equalisation)
CLAHE_CLIP_LIMIT:   float = 3.0
CLAHE_TILE_GRID:    tuple = (8, 8)

# FFT watermark analysis — mid-band annulus (inner_r, outer_r) as fraction of half-width
FFT_INNER_RATIO:  float = 0.05
FFT_OUTER_RATIO:  float = 0.35

# Laplacian sharpness — relaxed for phone camera blur and lighting variation
# A genuine note photographed on a phone will have soft edges due to depth-of-field
LAPLACIAN_GENUINE_THRESHOLD:  float = 60.0    # relaxed from 80 — accounts for phone blur
LAPLACIAN_SUSPECT_THRESHOLD:  float = 20.0    # relaxed from 30

# FFT watermark thresholds — relaxed for phone camera lighting variation
# A genuine watermark under imperfect lighting will score lower than under a scanner lamp
FFT_GENUINE_THRESHOLD:  float = 0.35   # relaxed from 0.45 — phone lighting reduces FFT energy
FFT_SUSPECT_THRESHOLD:  float = 0.25   # was 0.50

# Sobel bleed-line thresholds — minimum edge count per denomination
# Phone photos produce many connected components; using higher thresholds
BLEED_LINE_THRESHOLDS: dict[int, int] = {
    100:  30,
    200:  35,
    500:  40,
    2000: 45,
    0:    30,   # unknown denomination fallback
}

# ─────────────────────────────────────────────────────────────────────────────
# Lazy singleton — shared Groq client
# ─────────────────────────────────────────────────────────────────────────────

_groq_client: Optional[AsyncGroq] = None


def _get_groq_client() -> AsyncGroq:
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncGroq(api_key=GROQ_API_KEY, timeout=GROQ_TIMEOUT)
        logger.info("Groq vision client initialised (model=%s)", GROQ_VISION_MODEL)
    return _groq_client


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Schema — CounterfeitResult
# ─────────────────────────────────────────────────────────────────────────────

class OpenCVMetrics(BaseModel):
    """Raw numeric outputs from the forensic sub-routines — stored in Supabase JSONB."""
    clahe_contrast_score: float = Field(ge=0.0, le=1.0)
    fft_watermark_opacity: float = Field(ge=0.0, le=1.0)
    laplacian_variance: float = Field(ge=0.0)
    sobel_edge_density: float = Field(ge=0.0, le=1.0)
    bleed_line_count: int = Field(ge=0)


class CounterfeitResult(BaseModel):
    """Canonical output contract for the counterfeit detection pipeline."""

    # ── Core verdict ─────────────────────────────────────────────────────────
    verdict:     str   = Field(description="GENUINE | SUSPECT | COUNTERFEIT")
    final_score: int   = Field(description="0 (definite counterfeit) to 100 (definite genuine)")
    confidence:  float = Field(ge=0.0, le=1.0)
    denomination: int  = Field(default=0, description="Detected denomination: 100/200/500/2000")

    # ── Feature report ────────────────────────────────────────────────────────
    features_passed: list[str] = Field(default_factory=list)
    features_failed: list[str] = Field(default_factory=list)

    # ── Raw forensic metrics (for branch audit log) ───────────────────────────
    opencv_metrics: OpenCVMetrics

    # ── Human-readable output ─────────────────────────────────────────────────
    explanation:         str        = Field(description="Teller-facing explanation of verdict")
    recommended_actions: list[str]  = Field(default_factory=list)

    # ── Pipeline metadata ─────────────────────────────────────────────────────
    model_used:          str   = Field(default=GROQ_VISION_MODEL)
    processing_time_ms:  float = Field(default=0.0)

    @field_validator("verdict")
    @classmethod
    def normalise_verdict(cls, v: str) -> str:
        v = v.upper().strip()
        valid = {"GENUINE", "SUSPECT", "COUNTERFEIT"}
        return v if v in valid else "SUSPECT"   # conservative fallback

    @field_validator("final_score")
    @classmethod
    def clamp_score(cls, v: int) -> int:
        return max(0, min(100, v))

    @model_validator(mode="after")
    def sync_verdict_score(self) -> "CounterfeitResult":
        """
        Only correct extreme contradictions — trust Groq vision verdict primarily.
        OpenCV pre-score is supplementary; phone photo quality varies widely.
        """
        # Only override if score is extremely contradictory
        if self.final_score >= 85 and self.verdict == "COUNTERFEIT":
            self.verdict = "SUSPECT"
        if self.final_score <= 15 and self.verdict == "GENUINE":
            self.verdict = "SUSPECT"
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Internal dataclass — intermediate result from OpenCV stage
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class _CVAnalysis:
    """
    Holds every intermediate artefact produced by the OpenCV pipeline so the
    vision prompt stage has rich numeric context without re-running any math.
    """
    enhanced_jpg_bytes: bytes           # CLAHE-processed image re-encoded as JPEG
    metrics:            OpenCVMetrics
    pre_score:          int             # 0-100 OpenCV-only score (primes LLaVA)
    features_passed:    list[str] = field(default_factory=list)
    features_failed:    list[str] = field(default_factory=list)
    denomination_hint:  int = 0         # 0 = could not determine from image alone


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Image decode and resize guard
# ─────────────────────────────────────────────────────────────────────────────

def _decode_image(image_bytes: bytes) -> np.ndarray:
    """
    Decode raw bytes to a BGR numpy array.
    Downscales images that exceed MAX_DIMENSION_PX on either axis (preserves AR).
    Raises ValueError on corrupt or empty data.
    """
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError(
            f"Image too large: {len(image_bytes):,} bytes (max {MAX_IMAGE_BYTES:,})"
        )

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("cv2.imdecode returned None — image data is corrupt or unsupported.")

    h, w = img.shape[:2]
    if max(h, w) > MAX_DIMENSION_PX:
        scale = MAX_DIMENSION_PX / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        logger.debug("Image downscaled from %dx%d to %dx%d", w, h, new_w, new_h)

    return img


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — CLAHE contrast enhancement
# ─────────────────────────────────────────────────────────────────────────────

def _apply_clahe(bgr: np.ndarray) -> tuple[np.ndarray, float]:
    """
    Convert to LAB, apply CLAHE on the L channel only (preserves colour fidelity),
    convert back to BGR.

    Returns (enhanced_bgr, contrast_score).
    contrast_score is the ratio of enhanced L-channel std-dev to theoretical max (127.5),
    normalised to [0, 1] — indicates how much useful contrast the note image contains.
    """
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    clahe = cv2.createCLAHE(
        clipLimit=CLAHE_CLIP_LIMIT,
        tileGridSize=CLAHE_TILE_GRID,
    )
    l_enhanced = clahe.apply(l_channel)

    # Contrast score: std of enhanced L relative to max possible
    contrast_score = float(np.std(l_enhanced.astype(np.float32)) / 127.5)
    contrast_score = min(1.0, contrast_score)

    lab_enhanced = cv2.merge([l_enhanced, a_channel, b_channel])
    bgr_enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
    return bgr_enhanced, contrast_score


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — FFT watermark opacity analysis
# ─────────────────────────────────────────────────────────────────────────────

def _fft_watermark_opacity(bgr: np.ndarray) -> float:
    """
    Analyse the frequency domain to detect the RBI security watermark.

    Method:
      1. Convert to greyscale.
      2. Compute 2D DFT via numpy.fft.fft2 and shift zero-frequency to centre.
      3. Compute the magnitude spectrum (log-scaled for numerical stability).
      4. Build a binary annular mask covering the mid-frequency band
         (FFT_INNER_RATIO to FFT_OUTER_RATIO of the half-image width).
         Genuine watermarks embed their spatial energy in this band.
      5. Return the mean magnitude inside the annulus, normalised to [0, 1].

    Interpretation:
      ≥ 0.75  → strong watermark signature (GENUINE)
      0.50–0.74 → degraded watermark (SUSPECT)
      < 0.50  → watermark absent or printed surface-only (COUNTERFEIT)
    """
    grey = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = grey.shape

    # 2D DFT
    dft = np.fft.fft2(grey)
    dft_shift = np.fft.fftshift(dft)
    magnitude = np.log1p(np.abs(dft_shift))   # log1p avoids log(0)

    # Annular mask in frequency domain
    cy, cx = h // 2, w // 2
    y_idx, x_idx = np.ogrid[:h, :w]
    dist = np.sqrt((x_idx - cx) ** 2 + (y_idx - cy) ** 2)
    half_w = w / 2.0
    inner_r = FFT_INNER_RATIO * half_w
    outer_r = FFT_OUTER_RATIO * half_w
    mask = (dist >= inner_r) & (dist <= outer_r)

    # Normalise: mean in-band magnitude relative to overall max
    in_band_mean  = float(np.mean(magnitude[mask]))
    overall_max   = float(np.max(magnitude)) if np.max(magnitude) > 0 else 1.0
    opacity_score = min(1.0, in_band_mean / overall_max)

    return opacity_score


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Laplacian variance for intaglio print sharpness
# ─────────────────────────────────────────────────────────────────────────────

def _laplacian_variance(bgr: np.ndarray) -> float:
    """
    Measure intaglio printing sharpness via the variance of the Laplacian operator.

    Genuine Indian currency notes are printed with intaglio (engraved plate) printing
    which produces physically raised ink with extremely sharp edges.
    Counterfeit notes (inkjet/laser) have softer edges → lower Laplacian variance.

    Threshold guidance:
      ≥ 150   → sharp intaglio relief detected (GENUINE)
      60–149  → borderline (SUSPECT)
      < 60    → flat, non-intaglio printing (COUNTERFEIT)
    """
    grey = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(grey, cv2.CV_64F)
    variance = float(laplacian.var())
    return variance


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Sobel edge density for bleed-line geometry
# ─────────────────────────────────────────────────────────────────────────────

def _sobel_bleed_lines(bgr: np.ndarray, denomination: int = 0) -> tuple[float, int]:
    """
    Use horizontal Sobel derivatives to detect vertical bleed lines at note edges.

    Method:
      1. Isolate the left ~12 % and right ~12 % edge strips (bleed lines are margin features).
      2. Apply Sobel X-gradient to find vertical edges.
      3. Binarise with Otsu thresholding.
      4. Count distinct vertical line clusters via connected-component analysis.
      5. Return (edge_density, line_count).

    Genuine ₹500: typically 12–16 clearly separated bleed lines per edge.
    Counterfeits often show fewer (2–5) or none.
    """
    grey = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = grey.shape

    # Crop left + right edge strips
    strip_w = max(1, int(w * 0.12))
    left_strip  = grey[:, :strip_w]
    right_strip = grey[:, w - strip_w:]
    combined = np.hstack([left_strip, right_strip])

    # Sobel X gradient
    sobel_x = cv2.Sobel(combined, cv2.CV_64F, 1, 0, ksize=3)
    sobel_abs = np.uint8(np.clip(np.abs(sobel_x), 0, 255))

    # Otsu binarisation
    _, binary = cv2.threshold(sobel_abs, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Edge density — fraction of edge pixels that are active
    edge_density = float(np.count_nonzero(binary)) / binary.size

    # Connected component count as bleed-line proxy
    num_labels, _ = cv2.connectedComponents(binary)
    line_count = max(0, num_labels - 1)   # subtract background label

    return edge_density, line_count


# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — Aggregate OpenCV metrics into feature report + pre-score
# ─────────────────────────────────────────────────────────────────────────────

def _run_opencv_pipeline(image_bytes: bytes) -> _CVAnalysis:
    """
    Synchronous full OpenCV forensic pipeline.
    CPU-bound — caller must offload to a thread pool executor.

    Returns _CVAnalysis with all intermediate artefacts.
    """
    # ── 1. Decode ─────────────────────────────────────────────────────────
    bgr_original = _decode_image(image_bytes)

    # ── 2. CLAHE enhancement ──────────────────────────────────────────────
    bgr_enhanced, contrast_score = _apply_clahe(bgr_original)

    # ── 3. FFT watermark opacity ──────────────────────────────────────────
    fft_opacity = _fft_watermark_opacity(bgr_enhanced)

    # ── 4. Laplacian variance ─────────────────────────────────────────────
    lap_variance = _laplacian_variance(bgr_enhanced)

    # ── 5. Sobel bleed lines ──────────────────────────────────────────────
    edge_density, line_count = _sobel_bleed_lines(bgr_enhanced)

    # ── 6. Feature pass/fail classification ───────────────────────────────
    features_passed: list[str] = []
    features_failed: list[str] = []

    # Watermark
    if fft_opacity >= FFT_GENUINE_THRESHOLD:
        features_passed.append("watermark_opacity")
    elif fft_opacity >= FFT_SUSPECT_THRESHOLD:
        features_failed.append("watermark_opacity")   # degraded
    else:
        features_failed.append("watermark_opacity")

    # Intaglio sharpness
    if lap_variance >= LAPLACIAN_GENUINE_THRESHOLD:
        features_passed.append("intaglio_sharpness")
    elif lap_variance >= LAPLACIAN_SUSPECT_THRESHOLD:
        features_failed.append("intaglio_sharpness")
    else:
        features_failed.append("intaglio_sharpness")

    # Contrast / scan quality
    if contrast_score >= 0.55:
        features_passed.append("scan_quality")
    else:
        features_failed.append("scan_quality")

    # Bleed lines
    min_lines = BLEED_LINE_THRESHOLDS.get(0, 8)  # denomination resolved by LLaVA
    if line_count >= min_lines:
        features_passed.append("bleed_lines")
    else:
        features_failed.append("bleed_lines")

    # Edge density (general structural complexity of the note surface)
    # Phone photos always have high edge density from texture — lower threshold
    if edge_density >= 0.15:
        features_passed.append("surface_complexity")
    else:
        features_failed.append("surface_complexity")

    # ── 7. Weighted pre-score (OpenCV-only, range 0-100) ──────────────────
    #  Weights reflect forensic importance:
    #    watermark  40 pts  — hardest to fake
    #    intaglio   30 pts  — physically impossible on home printers
    #    bleed      15 pts
    #    surface    10 pts
    #    contrast    5 pts
    score = 0
    if "watermark_opacity" in features_passed:
        score += 40
    elif fft_opacity >= FFT_SUSPECT_THRESHOLD:
        score += 20   # partial credit for degraded watermark
    if "intaglio_sharpness" in features_passed:
        score += 30
    elif lap_variance >= LAPLACIAN_SUSPECT_THRESHOLD:
        score += 15
    if "bleed_lines" in features_passed:
        score += 15
    if "surface_complexity" in features_passed:
        score += 10
    if "scan_quality" in features_passed:
        score += 5

    # ── 8. Re-encode CLAHE-enhanced image to JPEG for LLaVA ──────────────
    success, jpg_buf = cv2.imencode(
        ".jpg",
        bgr_enhanced,
        [cv2.IMWRITE_JPEG_QUALITY, 88],
    )
    if not success:
        raise RuntimeError("cv2.imencode failed — could not re-encode enhanced image.")
    enhanced_jpg_bytes = jpg_buf.tobytes()

    metrics = OpenCVMetrics(
        clahe_contrast_score=round(contrast_score, 4),
        fft_watermark_opacity=round(fft_opacity, 4),
        laplacian_variance=round(lap_variance, 2),
        sobel_edge_density=round(edge_density, 4),
        bleed_line_count=line_count,
    )

    logger.debug(
        "OpenCV pipeline complete  pre_score=%d  fft=%.3f  lap=%.1f  "
        "lines=%d  contrast=%.3f",
        score, fft_opacity, lap_variance, line_count, contrast_score,
    )

    return _CVAnalysis(
        enhanced_jpg_bytes=enhanced_jpg_bytes,
        metrics=metrics,
        pre_score=score,
        features_passed=features_passed,
        features_failed=features_failed,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 7 — LLaVA system prompt construction
# ─────────────────────────────────────────────────────────────────────────────

_RBI_SECURITY_FEATURES = """
GENUINE RBI CURRENCY NOTE SECURITY FEATURES (reference):

1. WATERMARK          : Gandhi portrait watermark visible when held to light; embedded in paper, NOT printed.
2. SECURITY THREAD    : Windowed demetallised magnetic thread reading 'भारत' / 'RBI'. Shifts colour under tilt.
3. INTAGLIO PRINTING  : RBI Governor's signature, guarantee text, Ashoka pillar emblem, and denominational numeral are raised to the touch.
4. LATENT IMAGE       : Denominational numeral visible in angular viewing ('500' on ₹500, '2000' on ₹2000).
5. MICROLETTERING     : Text 'RBI' and denominational numeral visible under magnification below Gandhi portrait.
6. COLOUR SHIFT INK   : Numeral panel shifts from green to blue when tilted (₹500, ₹2000 only).
7. FLUORESCENT INK    : Numeral, RBI panel, and reverse design glow under UV lamp.
8. SEE-THROUGH DESIGN : Printed floral motif on obverse and reverse register perfectly when held to light.
9. BLEED LINES        : Seven angular bleed lines printed at left and right edges for visually impaired identification.
10. NUMBERING PANEL   : Ascending-size numerals, printed in fluorescent ink.
"""


def _build_vision_prompt(cv_analysis: _CVAnalysis) -> str:
    """
    Construct the forensic system prompt.
    Injects pre-computed OpenCV metrics so LLaVA acts as a cross-validation
    layer rather than doing all the reasoning blind.
    """
    passed_str = ", ".join(cv_analysis.features_passed) or "none"
    failed_str = ", ".join(cv_analysis.features_failed) or "none"
    m = cv_analysis.metrics

    return f"""You are SurakshaNet's bank-teller forensic vision AI. Determine whether the currency note is GENUINE, SUSPECT, or COUNTERFEIT. Be accurate, not overly strict.

{_RBI_SECURITY_FEATURES}

PRE-COMPUTED OPENCV METRICS (supplementary — not absolute verdicts):
  • CLAHE contrast score  : {m.clahe_contrast_score:.4f}
  • FFT watermark opacity : {m.fft_watermark_opacity:.4f}
  • Laplacian variance    : {m.laplacian_variance:.1f}
  • Sobel edge density    : {m.sobel_edge_density:.4f}
  • Bleed line count      : {m.bleed_line_count}
  • OpenCV pre-score      : {cv_analysis.pre_score}/100

OPENCV FEATURE REPORT:
  ✓ PASSED : {passed_str}
  ✗ FAILED : {failed_str}

CAMERA ARTIFACTS — ACCOUNT FOR THESE, DO NOT PENALIZE:
- Phone camera photos will have natural blur, uneven lighting, and slight distortion.
- Do NOT fail a note solely for blurriness — assess structural features instead.
- A faintly visible Gandhi portrait or security thread PASSES even if not razor-sharp.
- Lighting shadows on one side of the note are camera artifacts, not security failures.
- Slight colour cast from ambient lighting (yellow/blue tint) is normal for phone photos.

WHAT GENUINELY FAILS:
- Gandhi portrait completely absent (not just blurry)
- Security thread completely missing (not just hard to see due to angle)
- Note looks printed on plain paper with no texture or depth
- Denomination numerals or RBI text are clearly printed rather than embossed

ANALYSIS INSTRUCTIONS:
1. Look for the Gandhi watermark, security thread, and denomination numeral — these are primary.
2. If the overall note looks structurally correct with expected features visible, lean GENUINE.
3. Reserve COUNTERFEIT only for notes where multiple primary features are clearly absent/fake.
4. Most real notes shot on a phone should score 60-85 — calibrate accordingly.
5. Assign final_score, confidence, and list only features you can clearly assess.

VERDICT CALIBRATION:
  GENUINE     : final_score 65–100 — primary features present (even if slightly blurry)
  SUSPECT     : final_score 35–64  — some features unclear; recommend UV check
  COUNTERFEIT : final_score 0–34   — multiple primary features clearly absent or fake

CRITICAL OUTPUT RULES:
- Respond with ONLY a valid JSON object. No markdown, no prose.

{{
  "verdict": "<GENUINE|SUSPECT|COUNTERFEIT>",
  "final_score": <integer 0-100>,
  "confidence": <float 0.0-1.0>,
  "denomination": <100|200|500|2000|0>,
  "features_passed": ["<feature_name>", ...],
  "features_failed": ["<feature_name>", ...],
  "explanation": "<teller-facing explanation>",
  "recommended_actions": ["<action>", ...]
}}"""


# ─────────────────────────────────────────────────────────────────────────────
# Step 8 — Groq LLaVA vision inference
# ─────────────────────────────────────────────────────────────────────────────

async def _call_groq_vision(system_prompt: str, enhanced_jpg_bytes: bytes) -> str:
    """
    Call Groq llama-3.2-90b-vision-preview with the CLAHE-processed note image.

    The image is sent as a base64-encoded data URI in the OpenAI vision message format.
    Returns the raw JSON string from the model.
    """
    client = _get_groq_client()

    # Encode to base64 data URI
    b64_image = base64.b64encode(enhanced_jpg_bytes).decode("utf-8")
    data_uri  = f"data:image/jpeg;base64,{b64_image}"

    response = await client.chat.completions.create(
        model=GROQ_VISION_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": data_uri, "detail": "high"},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Perform a complete forensic analysis of this currency note image. "
                            "Use the pre-computed OpenCV metrics in the system prompt as "
                            "ground-truth numerical context. Return only the JSON verdict."
                        ),
                    },
                ],
            },
        ],
        temperature=GROQ_TEMPERATURE,
        max_tokens=GROQ_MAX_TOKENS,
        # Note: Groq vision endpoint may not support response_format JSON mode;
        # we enforce JSON via the prompt instead and parse defensively below.
    )

    raw = response.choices[0].message.content or ""
    logger.debug(
        "Groq vision response  tokens=%d  finish=%s",
        response.usage.total_tokens if response.usage else -1,
        response.choices[0].finish_reason,
    )
    return raw


# ─────────────────────────────────────────────────────────────────────────────
# Step 8b — Parse and validate LLaVA JSON output
# ─────────────────────────────────────────────────────────────────────────────

def _parse_vision_response(
    raw: str,
    cv_analysis: _CVAnalysis,
    elapsed_ms: float,
) -> CounterfeitResult:
    """
    Parse raw JSON from LLaVA and merge with the OpenCV artefacts.

    The OpenCV metrics are always authoritative — they are injected into the
    result regardless of what the model returns for those fields.
    """
    cleaned = raw.strip()

    # Strip accidental markdown fences
    fence = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()

    # Extract outermost JSON object
    obj_match = re.search(r"\{[\s\S]+\}", cleaned)
    if obj_match:
        cleaned = obj_match.group(0)

    data: dict[str, Any] = json.loads(cleaned)

    # Groq vision is the PRIMARY verdict authority.
    # OpenCV metrics are injected as numeric evidence but do NOT override
    # the model's visual assessment of features it can actually see in the image.
    # We only use OpenCV features_passed/failed as supplementary context.
    llava_passed = set(data.get("features_passed", []))
    llava_failed = set(data.get("features_failed", []))
    cv_passed    = set(cv_analysis.features_passed)
    cv_failed    = set(cv_analysis.features_failed)

    # Union of passed from either source; failed only if BOTH agree or Groq flags it
    merged_passed = list(llava_passed | (cv_passed - llava_failed))
    merged_failed = list(llava_failed | (cv_failed - llava_passed))
    # Ensure no overlap
    merged_failed = [f for f in merged_failed if f not in merged_passed]

    data["features_passed"]    = merged_passed
    data["features_failed"]    = merged_failed
    data["opencv_metrics"]     = cv_analysis.metrics
    data["model_used"]         = GROQ_VISION_MODEL
    data["processing_time_ms"] = round(elapsed_ms, 2)

    return CounterfeitResult(**data)


# ─────────────────────────────────────────────────────────────────────────────
# Step 9 — Persist scan to Supabase
# ─────────────────────────────────────────────────────────────────────────────

async def _persist_scan(
    scan_id: str,
    branch_code: Optional[str],
    result: CounterfeitResult,
) -> None:
    """
    Write the scan result to counterfeit_scans for branch analytics.
    Non-fatal — persistence failure never surfaces to the teller.
    """
    try:
        sql = """
            INSERT INTO counterfeit_scans (
                id, branch_code, denomination, verdict,
                confidence, opencv_flags, llava_response, scanned_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, now())
        """
        import json as _json  # avoid shadowing module-level json import
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
        logger.debug("Counterfeit scan persisted  id=%s  verdict=%s", scan_id, result.verdict)
    except Exception as exc:
        logger.warning("Scan persistence failed (non-fatal): %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Fallback helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cv_score_to_verdict_hint(pre_score: int) -> str:
    """Map the OpenCV pre-score to a demo fixture hint."""
    if pre_score >= 75:
        return "genuine"
    if pre_score >= 35:
        return "suspect"
    return "counterfeit"


def _fallback_result(
    cv_analysis: Optional[_CVAnalysis],
    t_start: float,
    reason: str = "unknown",
) -> CounterfeitResult:
    """
    Safe fallback result when the live pipeline fails.
    Uses demo fixture in DEMO_MOCK_MODE; otherwise returns conservative SUSPECT.
    """
    elapsed_ms = round((time.monotonic() - t_start) * 1000, 2)
    logger.warning("Counterfeit fallback triggered  reason=%s  elapsed=%.0f ms", reason, elapsed_ms)

    if DEMO_MOCK_MODE:
        hint = _cv_score_to_verdict_hint(cv_analysis.pre_score) if cv_analysis else "suspect"
        demo = get_demo_counterfeit_response(hint)
        demo["processing_time_ms"] = elapsed_ms
        demo["model_used"] = f"demo_fallback:{reason}"
        if cv_analysis:
            demo["opencv_metrics"] = cv_analysis.metrics
        else:
            # Provide zeroed-out metrics so the schema always validates
            demo["opencv_metrics"] = OpenCVMetrics(
                clahe_contrast_score=0.0,
                fft_watermark_opacity=0.0,
                laplacian_variance=0.0,
                sobel_edge_density=0.0,
                bleed_line_count=0,
            )
        return CounterfeitResult(**demo)

    # Production fallback — conservative SUSPECT, never silently pass a bad note
    metrics = cv_analysis.metrics if cv_analysis else OpenCVMetrics(
        clahe_contrast_score=0.0,
        fft_watermark_opacity=0.0,
        laplacian_variance=0.0,
        sobel_edge_density=0.0,
        bleed_line_count=0,
    )
    return CounterfeitResult(
        verdict="SUSPECT",
        final_score=40,
        confidence=0.40,
        denomination=0,
        features_passed=cv_analysis.features_passed if cv_analysis else [],
        features_failed=cv_analysis.features_failed if cv_analysis else [],
        opencv_metrics=metrics,
        explanation=(
            "Automated verification temporarily unavailable. "
            "As a precaution this note has been flagged as SUSPECT. "
            f"(Reason: {reason}). "
            "Please perform manual UV lamp verification before accepting."
        ),
        recommended_actions=[
            "Perform manual UV lamp and feel-based verification.",
            "Escalate to branch manager if uncertain.",
            "Do not return note to customer while verification is pending.",
            "Retry the automated scan — service should recover within minutes.",
        ],
        model_used=f"fallback:{reason}",
        processing_time_ms=elapsed_ms,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API — analyse_note()
# ─────────────────────────────────────────────────────────────────────────────

async def analyse_note(
    image_bytes: bytes,
    branch_code: Optional[str] = None,
    scan_id: Optional[str] = None,
    *,
    skip_persist: bool = False,
) -> CounterfeitResult:
    """
    Full counterfeit detection pipeline for a currency note image.

    Parameters
    ----------
    image_bytes  : Raw image bytes from the multipart upload (JPEG/PNG/WEBP).
    branch_code  : Bank branch identifier for analytics (e.g. 'SBI-MUM-042').
    scan_id      : UUID string for audit trail. Auto-generated if not provided.
    skip_persist : Set True in unit tests to avoid DB writes.

    Returns
    -------
    CounterfeitResult — always returns something; falls back to SUSPECT on error.

    Never raises — all exceptions are caught and converted to a safe fallback.
    """
    scan_id = scan_id or str(uuid.uuid4())
    t_start = time.monotonic()
    cv_analysis: Optional[_CVAnalysis] = None

    # ── Input guard ──────────────────────────────────────────────────────────
    if not image_bytes:
        return _fallback_result(None, t_start, reason="empty_image")

    # ── Demo / mock shortcut ─────────────────────────────────────────────────
    if DEMO_MOCK_MODE:
        logger.info("DEMO_MOCK_MODE active — returning canned counterfeit response.")
        demo = get_demo_counterfeit_response("suspect")   # neutral default for demo
        demo["processing_time_ms"] = round((time.monotonic() - t_start) * 1000, 2)
        return CounterfeitResult(**demo)

    # ── Live pipeline ────────────────────────────────────────────────────────
    try:
        # Step 1–6: OpenCV forensic sub-routines (CPU-bound → thread pool)
        loop = asyncio.get_running_loop()
        cv_analysis = await loop.run_in_executor(
            None, _run_opencv_pipeline, image_bytes
        )

        logger.info(
            "OpenCV complete  scan=%s  pre_score=%d  fft=%.3f  lap=%.1f  lines=%d",
            scan_id,
            cv_analysis.pre_score,
            cv_analysis.metrics.fft_watermark_opacity,
            cv_analysis.metrics.laplacian_variance,
            cv_analysis.metrics.bleed_line_count,
        )

        # Step 7: Build vision prompt with injected metrics
        system_prompt = _build_vision_prompt(cv_analysis)

        # Step 8: Groq LLaVA 90B vision inference
        raw_response = await _call_groq_vision(system_prompt, cv_analysis.enhanced_jpg_bytes)

        # Step 8b: Parse + validate + merge with OpenCV artefacts
        elapsed_ms = (time.monotonic() - t_start) * 1000
        result = _parse_vision_response(raw_response, cv_analysis, elapsed_ms)

        # Step 9: Persist (fire and forget)
        if not skip_persist:
            asyncio.create_task(_persist_scan(scan_id, branch_code, result))

        logger.info(
            "CounterfeitAnalysis complete  scan=%s  verdict=%s  score=%d  "
            "confidence=%.2f  elapsed=%.0f ms",
            scan_id, result.verdict, result.final_score,
            result.confidence, result.processing_time_ms,
        )
        return result

    # ── Granular exception handling — mirrors scam_agent.py pattern ──────────
    except ValueError as exc:
        # Bad image data — don't retry, report clearly
        logger.error("Invalid image input  scan=%s: %s", scan_id, exc)
        return _fallback_result(cv_analysis, t_start, reason=f"invalid_image:{exc}")

    except (APITimeoutError, asyncio.TimeoutError) as exc:
        logger.error("Groq vision timeout  scan=%s: %s", scan_id, exc)
        return _fallback_result(cv_analysis, t_start, reason="groq_timeout")

    except RateLimitError as exc:
        logger.error("Groq rate limit  scan=%s: %s", scan_id, exc)
        return _fallback_result(cv_analysis, t_start, reason="groq_rate_limit")

    except APIStatusError as exc:
        logger.error("Groq API error %d  scan=%s: %s", exc.status_code, scan_id, exc)
        return _fallback_result(cv_analysis, t_start, reason=f"groq_api_{exc.status_code}")

    except json.JSONDecodeError as exc:
        logger.error("JSON parse error  scan=%s: %s", scan_id, exc)
        # OpenCV analysis succeeded — build verdict from pre-score alone
        if cv_analysis:
            return _build_opencv_only_result(cv_analysis, t_start)
        return _fallback_result(None, t_start, reason="json_parse_error")

    except Exception as exc:
        logger.exception("Unexpected error  scan=%s: %s", scan_id, exc)
        return _fallback_result(cv_analysis, t_start, reason="unexpected_error")


# ─────────────────────────────────────────────────────────────────────────────
# OpenCV-only verdict — used when LLaVA fails but OpenCV succeeded
# ─────────────────────────────────────────────────────────────────────────────

def _build_opencv_only_result(cv_analysis: _CVAnalysis, t_start: float) -> CounterfeitResult:
    """
    Construct a CounterfeitResult using only OpenCV metrics when the vision
    model call fails or returns unparseable output.
    Confidence is capped at 0.65 to signal this is a partial result.
    """
    score = cv_analysis.pre_score
    if score >= 75:
        verdict, confidence = "GENUINE", 0.60
    elif score >= 35:
        verdict, confidence = "SUSPECT", 0.55
    else:
        verdict, confidence = "COUNTERFEIT", 0.65

    elapsed_ms = round((time.monotonic() - t_start) * 1000, 2)

    return CounterfeitResult(
        verdict=verdict,
        final_score=score,
        confidence=confidence,
        denomination=0,
        features_passed=cv_analysis.features_passed,
        features_failed=cv_analysis.features_failed,
        opencv_metrics=cv_analysis.metrics,
        explanation=(
            f"Vision model unavailable — verdict based on OpenCV forensic metrics only "
            f"(pre-score {score}/100). "
            f"FFT watermark opacity: {cv_analysis.metrics.fft_watermark_opacity:.3f}. "
            f"Laplacian variance: {cv_analysis.metrics.laplacian_variance:.1f}. "
            f"Manual UV lamp verification is strongly recommended."
        ),
        recommended_actions=[
            "Perform UV lamp verification to cross-check this automated result.",
            "Escalate to branch manager — full AI analysis was unavailable.",
            "Retry the scan if the issue persists.",
        ],
        model_used="opencv_only",
        processing_time_ms=elapsed_ms,
    )
