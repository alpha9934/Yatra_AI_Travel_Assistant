from dotenv import load_dotenv
load_dotenv()

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from middleware.auth import AuthMiddleware, LoggingMiddleware, InjectionGuardMiddleware, setup_logging
from routes import chat, expense, booking, disruption

setup_logging()
logger = logging.getLogger(__name__)

# ── App ──────────────────────────────────────────────────────────
app = FastAPI(
    title="Yatra AI Agent",
    version="2.0.0",
    description="Multi-agent corporate travel assistant with RAG + Supabase persistence",
)

# ── Middleware ───────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(InjectionGuardMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthMiddleware)

# ── Routes ───────────────────────────────────────────────────────
app.include_router(chat.router,       prefix="/api/chat",       tags=["chat"])
app.include_router(expense.router,    prefix="/api/expense",    tags=["expense"])
app.include_router(booking.router,    prefix="/api/booking",    tags=["booking"])
app.include_router(disruption.router, prefix="/api/disruption", tags=["disruption"])


# ── Health & readiness ───────────────────────────────────────────
@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/ready", tags=["ops"])
def ready():
    """Readiness probe — checks Supabase and Pinecone connectivity."""
    checks = {}

    try:
        from db.supabase_client import get_supabase
        db = get_supabase()
        db.table("bookings").select("id").limit(1).execute()
        checks["supabase"] = "ok"
    except Exception as exc:
        checks["supabase"] = f"error: {exc}"

    try:
        from rag.pinecone_rag import _get_index
        _get_index()
        checks["pinecone"] = "ok"
    except Exception as exc:
        checks["pinecone"] = f"error: {exc}"

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={"status": "ready" if all_ok else "degraded", "checks": checks},
    )


# ── Admin ────────────────────────────────────────────────────────
@app.post("/admin/ingest-policy", tags=["admin"])
async def ingest_policy():
    """Trigger policy document ingestion into Pinecone. One-time setup."""
    from rag.pinecone_rag import ingest_policy_docs
    result = await ingest_policy_docs()
    return result


# ── Root ─────────────────────────────────────────────────────────
@app.get("/", tags=["ops"])
def root():
    return {"status": "Yatra AI Agent v2.0 running", "docs": "/docs"}