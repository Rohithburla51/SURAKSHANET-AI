"""
backend/api/routes/scam.py
━━━━━━━━━━━━━━━━━━━━━━━━━━
SurakshaNet AI — Citizen Scam Analysis Routes
Phase 3: REST API  |  Model: DeepSeek 3.2 (0.25x)

Endpoints:
  POST /api/scam/analyze/text   — paste suspicious SMS/WhatsApp text
  POST /api/scam/analyze/audio  — upload a phone-call audio recording
  POST /api/scam/analyze        — multipart form supporting both input types

All endpoints return ScamAnalysisResult.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile, File, status
from fastapi.responses import JSONResponse
from groq import AsyncGroq

from agents.scam_agent import analyse_text, ScamAnalysisResult

logger = logging.getLogger("surakshanet.routes.scam")

router = APIRouter()

# Max audio file size — 25 MB (Groq Whisper hard limit)
MAX_AUDIO_BYTES: int = 25 * 1024 * 1024
# Allowed audio MIME types
ALLOWED_AUDIO_MIME = {
    "audio/mpeg", "audio/mp3", "audio/mp4", "audio/wav",
    "audio/x-wav", "audio/webm", "audio/ogg", "audio/flac",
    "audio/x-m4a", "audio/m4a",
}

GROQ_API_KEY: str = os.environ["GROQ_API_KEY"]


# ─────────────────────────────────────────────────────────────────────────────
# Helper — transcribe audio via Groq Whisper then pipe into scam analysis
# ─────────────────────────────────────────────────────────────────────────────

async def _transcribe_audio(audio_bytes: bytes, filename: str) -> str:
    """
    Transcribe audio bytes using Groq Whisper Large v3.
    Returns the raw transcript string.
    Raises HTTPException(422) on transcription failure.
    """
    import httpx  # only needed for Groq file upload which uses multipart internally

    try:
        client = AsyncGroq(api_key=GROQ_API_KEY, timeout=60.0)
        # Groq SDK expects a file-like tuple: (filename, bytes, content_type)
        transcription = await client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=(filename, audio_bytes, "audio/mpeg"),
            response_format="text",
            language="hi",           # default Hindi; Whisper auto-detects if wrong
        )
        # SDK returns str when response_format="text"
        return transcription.strip() if isinstance(transcription, str) else transcription.text.strip()
    except Exception as exc:
        logger.error("Whisper transcription failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Audio transcription failed: {exc}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic request bodies
# ─────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field

class TextAnalysisRequest(BaseModel):
    text:       str           = Field(..., min_length=1, max_length=5000,
                                      description="Suspicious SMS, WhatsApp, or email text")
    session_id: Optional[str] = Field(None, description="Optional client-supplied session UUID")


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/analyze/text",
    response_model=ScamAnalysisResult,
    summary="Analyse suspicious text for scam indicators",
    description=(
        "Accepts a plain-text message (SMS, WhatsApp, email). "
        "Runs RAG + Groq 120B analysis. Returns risk score, category, "
        "manipulation tactics, red flags, and bilingual explanation."
    ),
)
async def analyze_text_endpoint(body: TextAnalysisRequest) -> ScamAnalysisResult:
    session_id = body.session_id or str(uuid.uuid4())
    logger.info("Text analysis request  session=%s  chars=%d", session_id, len(body.text))
    return await analyse_text(body.text, session_id=session_id)


@router.post(
    "/analyze/audio",
    response_model=ScamAnalysisResult,
    summary="Analyse a phone-call audio recording for scam indicators",
    description=(
        "Accepts an audio file (MP3/WAV/M4A/OGG/WEBM, max 25 MB). "
        "Transcribes via Groq Whisper, then pipes the transcript "
        "through the full scam analysis pipeline."
    ),
)
async def analyze_audio_endpoint(
    audio: UploadFile = File(..., description="Phone-call audio recording"),
    session_id: Optional[str] = Form(None),
) -> ScamAnalysisResult:
    # ── File validation ──────────────────────────────────────────────────────
    if audio.content_type and audio.content_type not in ALLOWED_AUDIO_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported audio type '{audio.content_type}'. "
                   f"Allowed: {', '.join(sorted(ALLOWED_AUDIO_MIME))}",
        )

    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio file too large ({len(audio_bytes):,} bytes). Max 25 MB.",
        )
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded audio file is empty.",
        )

    sid = session_id or str(uuid.uuid4())
    logger.info("Audio analysis request  session=%s  bytes=%d", sid, len(audio_bytes))

    # ── Transcribe ───────────────────────────────────────────────────────────
    transcript = await _transcribe_audio(audio_bytes, audio.filename or "recording.mp3")
    logger.info("Transcript ready  session=%s  chars=%d", sid, len(transcript))

    # ── Analyse transcript ───────────────────────────────────────────────────
    return await analyse_text(transcript, session_id=sid)


@router.post(
    "/analyze",
    response_model=ScamAnalysisResult,
    summary="Unified scam analysis — text or audio (multipart form)",
    description=(
        "Flexible endpoint that accepts either `text` (form field) OR "
        "`audio` (file upload). If both are provided, audio is transcribed "
        "and the transcript overrides the text field. "
        "Suitable for direct `<form>` POSTs from the citizen portal."
    ),
)
async def analyze_unified_endpoint(
    text:       Optional[str]        = Form(None),
    audio:      Optional[UploadFile] = File(None),
    session_id: Optional[str]        = Form(None),
) -> ScamAnalysisResult:
    sid = session_id or str(uuid.uuid4())

    if audio is not None and audio.filename:
        # Audio path
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=422, detail="Uploaded audio is empty.")
        if len(audio_bytes) > MAX_AUDIO_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Audio too large ({len(audio_bytes):,} bytes). Max 25 MB.",
            )
        transcript = await _transcribe_audio(audio_bytes, audio.filename or "recording.mp3")
        return await analyse_text(transcript, session_id=sid)

    if text and text.strip():
        return await analyse_text(text.strip(), session_id=sid)

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Provide either 'text' or 'audio' — both cannot be empty.",
    )
