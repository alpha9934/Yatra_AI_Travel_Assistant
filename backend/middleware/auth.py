"""
Auth & Logging Middleware
- API key authentication via X-API-Key header
- Structured JSON logging for every request
- Request ID injection for tracing
- Prompt injection detection
"""
import os
import json
import time
import uuid
import logging
import re
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Load valid API keys from env (comma-separated)
_VALID_KEYS: set[str] = set(
    k.strip() for k in os.environ.get("API_KEYS", "").split(",") if k.strip()
)

# Paths that don't require auth
PUBLIC_PATHS = {"/", "/docs", "/openapi.json", "/redoc", "/health", "/ready", "/admin/ingest-policy", "/api/chat/", "/api/chat", "/api/booking/flights", "/api/booking/hotels"}

# Prompt injection patterns to detect and sanitize
_INJECTION_PATTERNS = [
    r"ignore (previous|all|above) instructions",
    r"you are now",
    r"disregard (your|the) (system|instructions)",
    r"pretend (you are|to be)",
    r"act as (if|though)",
    r"jailbreak",
    r"DAN mode",
    r"forget (everything|your) (you|you've|previously)",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def setup_logging():
    """Configure structured JSON logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[logging.StreamHandler()],
    )

    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log = {
                "ts":      self.formatTime(record),
                "level":   record.levelname,
                "logger":  record.name,
                "msg":     record.getMessage(),
            }
            if hasattr(record, "extra"):
                log.update(record.extra)
            return json.dumps(log)

    for handler in logging.root.handlers:
        handler.setFormatter(JsonFormatter())


def detect_prompt_injection(text: str) -> bool:
    """Returns True if the text contains prompt injection patterns."""
    return bool(_INJECTION_RE.search(text))


class AuthMiddleware(BaseHTTPMiddleware):
    """Validates X-API-Key header on all protected routes."""

    async def dispatch(self, request: Request, call_next):
        # If no API keys configured, allow all requests (local dev mode)
        if not _VALID_KEYS:
            return await call_next(request)
        if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/docs"):
            return await call_next(request)

        api_key = request.headers.get("X-API-Key", "")
        if api_key not in _VALID_KEYS:
            logger.warning(f"auth_failed path={request.url.path} key_prefix={api_key[:8] if api_key else 'none'}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key. Pass X-API-Key header."},
            )
        return await call_next(request)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with method, path, status, latency, and request ID."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start = time.time()

        response = await call_next(request)

        latency_ms = int((time.time() - start) * 1000)
        logger.info(json.dumps({
            "ts":         time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "request_id": request_id,
            "method":     request.method,
            "path":       request.url.path,
            "status":     response.status_code,
            "latency_ms": latency_ms,
        }))
        response.headers["X-Request-ID"] = request_id
        return response


class InjectionGuardMiddleware(BaseHTTPMiddleware):
    """
    Scans incoming JSON bodies for prompt injection patterns.
    Blocks requests that contain known injection phrases.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH") and "application/json" in request.headers.get("content-type", ""):
            try:
                body_bytes = await request.body()
                body_text = body_bytes.decode("utf-8", errors="ignore")
                if detect_prompt_injection(body_text):
                    logger.warning(f"prompt_injection_detected path={request.url.path}")
                    return JSONResponse(
                        status_code=400,
                        content={"detail": "Request contains disallowed content patterns."},
                    )
                # Rebuild the request body for downstream handlers
                async def receive():
                    return {"type": "http.request", "body": body_bytes}
                request._receive = receive
            except Exception:
                pass  # Don't block on parse errors

        return await call_next(request)
