import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

from app.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("GraphRAG Medical Research Assistant starting up...")
    logger.info("All pipeline components initialized")
    yield
    # Shutdown
    logger.info("GraphRAG Medical Research Assistant shutting down...")

app = FastAPI(
    title="GraphRAG Medical Research Assistant",
    description="Self-improving medical AI with hybrid retrieval, graph reasoning, and hallucination detection",
    version="2.0.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    logger.info(f"{request.method} {request.url.path} — {response.status_code} — {process_time:.3f}s")
    return response

# Register API routes
app.include_router(router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {
        "message": "GraphRAG Medical Research Assistant API v2.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}")
    return JSONResponse(status_code=500, content={"detail": str(exc)})
