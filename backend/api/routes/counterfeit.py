"""
backend/api/routes/counterfeit.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SurakshaNet AI — Bank Teller Counterfeit Detection Routes
Phase 3: REST API  |  Model: DeepSeek 3.2 (0.25x)

Endpoints:
  POST /api/counterfeit/scan   — upload note image + optional metadata
  GET  /api/counterfeit/denominations — list supported denominations

Returns CounterfeitResult (verdict: GENUINE | SUSPECT | COUNTERFEIT).
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from agents.counterfeit_agent import analyse_note, CounterfeitResult

logger = logging.getLogger("surakshanet.routes.counterfeit")

router = APIRouter()

# Supported image types — same set as OpenCV imdecode
ALLOWED_IMAGE_MIME = {
    "image/jpeg", "image/jpg", "image/png",
    "image/webp", "image/bmp", "image/tiff",
}

VALID_DENOMINATIONS = {100, 200, 500, 2000}
MAX_IMAGE_BYTES = 15 * 1024 * 1024     # 15 MB (matches counterfeit_agent cap)


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/scan",
    response_model=CounterfeitResult,
    summary="Scan a currency note image for counterfeiting",
    description=(
        "Upload a JPEG/PNG/WEBP image of a currency note. "
        "Runs CLAHE enhancement → FFT watermark analysis → Laplacian sharpness "
        "→ Groq LLaVA 90B vision verdict. "
        "Returns GENUINE, SUSPECT, or COUNTERFEIT with detailed forensic metrics."
    ),
)
async def scan_note(
    image: UploadFile = File(
        ...,
        description="Photo of the currency note (JPEG/PNG/WEBP, max 15 MB)",
    ),
    denomination: Optional[int] = Form(
        None,
        description="Declared denomination in INR: 100 | 200 | 500 | 2000",
    ),
    branch_code: Optional[str] = Form(
        None,
        max_length=32,
        description="Bank branch code for audit log (e.g. 'SBI-MUM-042')",
    ),
    scan_id: Optional[str] = Form(
        None,
        description="Client-supplied UUID for this scan (auto-generated if omitted)",
    ),
) -> CounterfeitResult:
    # ── File type validation ─────────────────────────────────────────────────
    content_type = (image.content_type or "").lower()
    if content_type and content_type not in ALLOWED_IMAGE_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported image type '{content_type}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_IMAGE_MIME))}"
            ),
        )

    # ── Read bytes ───────────────────────────────────────────────────────────
    image_bytes = await image.read()

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded image is empty.",
        )
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Image too large ({len(image_bytes):,} bytes). "
                f"Maximum allowed is {MAX_IMAGE_BYTES // (1024*1024)} MB."
            ),
        )

    # ── Denomination validation (soft — agents handle 0 as unknown) ──────────
    if denomination is not None and denomination not in VALID_DENOMINATIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid denomination {denomination}. "
                f"Must be one of: {sorted(VALID_DENOMINATIONS)}"
            ),
        )

    sid = scan_id or str(uuid.uuid4())
    logger.info(
        "Counterfeit scan request  scan=%s  branch=%s  denom=%s  bytes=%d",
        sid, branch_code, denomination, len(image_bytes),
    )

    return await analyse_note(
        image_bytes=image_bytes,
        branch_code=branch_code,
        scan_id=sid,
    )


@router.get(
    "/denominations",
    summary="List supported currency denominations",
    response_description="Sorted list of INR denominations accepted by the scanner",
)
async def get_denominations():
    """Returns the set of denominations the vision model is trained to verify."""
    return {
        "denominations": sorted(VALID_DENOMINATIONS),
        "currency": "INR",
        "note": "Pass denomination=0 if unknown — the model will attempt auto-detection.",
    }
