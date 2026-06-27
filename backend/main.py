"""
backend/main.py
━━━━━━━━━━━━━━━
SurakshaNet AI — FastAPI Application Entrypoint
Phase 3: REST API Core Routers  |  Model: DeepSeek 3.2 (0.25x)

Responsibilities:
  • Create the FastAPI application instance
  • Register CORS middleware (open for hackathon; tighten per-env in production)
  • Attach the async lifespan handler that boots/tears down all DB connections
  • Mount the four domain routers under /api/*
  • Expose /health and /ready endpoints
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from services.database import startup_databases, shutdown_databases, health_check_all
from api.routes import scam, counterfeit, network

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("surakshanet.main")

DEMO_MOCK_MODE: bool = os.getenv("DEMO_MOCK_MODE", "false").lower() == "true"


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan — startup + teardown
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Boot all storage backends before serving; close them on shutdown."""
    logger.info("SurakshaNet AI starting up …  DEMO_MOCK_MODE=%s", DEMO_MOCK_MODE)
    try:
        await startup_databases()
        logger.info("✅  All storage backends online.")
    except Exception as exc:
        # In demo/dev mode, DB failures are non-fatal — agents fall back to
        # demo_responses.py fixtures automatically.
        logger.warning(
            "⚠️  Storage backend startup failed (%s). "
            "Running in degraded/demo mode — all agents will use mock responses.",
            exc,
        )
    logger.info("✅  SurakshaNet AI is ready to serve requests.")
    yield
    logger.info("SurakshaNet AI shutting down …")
    try:
        await shutdown_databases()
    except Exception:
        pass
    logger.info("All connections closed. Goodbye.")


# ─────────────────────────────────────────────────────────────────────────────
# Application
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SurakshaNet AI API",
    version="2.0.0",
    description=(
        "Unified cybercrime intelligence API for Indian citizens, "
        "bank tellers, and law enforcement."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─────────────────────────────────────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # tighten to specific origins before production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Domain Routers
# ─────────────────────────────────────────────────────────────────────────────

app.include_router(scam.router,        prefix="/api/scam",        tags=["Citizen — Scam Analysis"])
app.include_router(counterfeit.router, prefix="/api/counterfeit", tags=["Bank — Counterfeit Detection"])
app.include_router(network.router,     prefix="/api/network",     tags=["Police — Fraud Network"])

# ─────────────────────────────────────────────────────────────────────────────
# Health & Readiness Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"], summary="Full health check with DB latency")
async def health():
    try:
        db_status = await health_check_all()
    except Exception as exc:
        db_status = {"overall": "degraded", "postgres": {"status": "error", "detail": str(exc)}, "neo4j": {"status": "error", "detail": str(exc)}}
    status_code = 200 if db_status["overall"] == "ok" else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status":    db_status["overall"],
            "stack":     "HuggingFace + Supabase + Neo4j Aura + Groq",
            "demo_mode": DEMO_MOCK_MODE,
            "databases": {
                "postgres": db_status.get("postgres"),
                "neo4j":    db_status.get("neo4j"),
            },
        },
    )


@app.get("/ready", tags=["System"], summary="Lightweight liveness probe")
async def ready():
    """Instant 200 used by Hugging Face Spaces liveness probes."""
    return {"status": "ok"}
