"""FastAPI main application entrypoint for The Lenny Growth Assistant."""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import time
import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.core.logging import setup_logger
from app.db.session import init_db
from app.api.routes import router as api_router

logger = setup_logger("fastapi_main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database tables and resources."""
    logger.info("Starting up %s v%s...", settings.PROJECT_NAME, settings.VERSION)
    init_db()

    # Cold-start auto-ingestion: populate knowledge base if empty
    try:
        from app.db.session import get_db_session
        from app.db.models import TranscriptChunk
        with get_db_session() as db:
            chunk_count = db.query(TranscriptChunk).count()
            if chunk_count == 0:
                logger.info("No transcript chunks found in database. Starting cold-start auto-ingestion...")
                from ingestion.ingest import ingest_all_transcripts
                total_ingested = ingest_all_transcripts()
                logger.info("Cold-start auto-ingestion complete: %d chunks indexed.", total_ingested)
            else:
                logger.info("Found %d indexed transcript chunks in database.", chunk_count)
    except Exception as e:
        logger.warning("Cold-start auto-ingestion warning: %s", e)

    logger.info("Startup complete. Ready to receive requests.")
    yield
    logger.info("Shutting down %s...", settings.PROJECT_NAME)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Evidence-grounded AI Growth Strategist backed by PostgreSQL + pgvector and Dual-Model LLM Bridge.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ============================================================================
# CORS Middleware
# ============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Request ID & Latency Telemetry Middleware
# ============================================================================
@app.middleware("http")
async def request_telemetry_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:10]}"
    request.state.request_id = request_id
    t0 = time.perf_counter()

    response = await call_next(request)

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-MS"] = str(latency_ms)

    # Log non-health requests
    if not request.url.path.startswith("/health"):
        logger.info(
            "%s %s -> %d (%.2f ms)",
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
            extra={"extra_data": {"request_id": request_id, "status_code": response.status_code, "latency_ms": latency_ms}}
        )
    return response

# ============================================================================
# Structured Error Handlers
# ============================================================================
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = getattr(request.state, "request_id", f"req_{uuid.uuid4().hex[:10]}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "request_id": request_id,
            "error_code": f"HTTP_{exc.status_code}",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", f"req_{uuid.uuid4().hex[:10]}")
    errors = jsonable_encoder(exc.errors())
    error_msg = errors[0]["msg"] if errors else "Request validation failed"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": error_msg,
            "details": errors,
            "request_id": request_id,
            "error_code": "VALIDATION_ERROR",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", f"req_{uuid.uuid4().hex[:10]}")
    logger.exception("Unhandled server exception for request %s: %s", request_id, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "An internal server error occurred.",
            "request_id": request_id,
            "error_code": "INTERNAL_SERVER_ERROR",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        },
    )

# Include API Router
app.include_router(api_router)
