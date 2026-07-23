"""
FastAPI Main Application Entry Point.

Initializes FastAPI app, configures CORS & request logging middleware,
and registers all modular API routers under prefix /api/v1.
"""

import logging
import sys
import time
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.routers import (
    companies,
    documents,
    health,
    market_cap,
    peers,
    portfolio,
    screener,
    sectors,
    valuation,
)

# Configure logger for FastAPI application
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("api_main")
logger.setLevel(logging.INFO)

if not logger.handlers:
    log_file = LOG_DIR / "api_requests.log"
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# 1. Initialize FastAPI App
app = FastAPI(
    title="Nifty 100 Financial Intelligence Platform API",
    description="REST API server exposing financial analytics, stock screening, valuation, cashflow intelligence, PDF reports, and portfolio metrics.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 2. Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configured for development; easily restricted for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 3. Request Logging Middleware
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    """
    Middleware that measures total response time and logs incoming HTTP requests.
    Example log format:
        GET    /api/v1/health                  200    14 ms
    """
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000.0

    method = request.method
    path = request.url.path
    status_code = response.status_code

    log_line = f"{method:<6s} {path:<30s} {status_code:<3d} {duration_ms:4.0f} ms"
    logger.info(log_line)

    # Expose custom header with processing time
    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
    return response


# 4. Register Modular Routers with Common API Prefix /api/v1
API_PREFIX = "/api/v1"
app.include_router(health.router, prefix=API_PREFIX)
app.include_router(companies.router, prefix=API_PREFIX)
app.include_router(screener.router, prefix=API_PREFIX)
app.include_router(sectors.router, prefix=API_PREFIX)
app.include_router(peers.router, prefix=API_PREFIX)
app.include_router(valuation.router, prefix=API_PREFIX)
app.include_router(market_cap.router, prefix=API_PREFIX)
app.include_router(portfolio.router, prefix=API_PREFIX)
app.include_router(documents.router, prefix=API_PREFIX)

# Also mount routers without /api/v1 prefix for direct root endpoint access
app.include_router(health.router, include_in_schema=False)
app.include_router(companies.router, include_in_schema=False)
app.include_router(screener.router, include_in_schema=False)
app.include_router(sectors.router, include_in_schema=False)
app.include_router(peers.router, include_in_schema=False)
app.include_router(valuation.router, include_in_schema=False)
app.include_router(market_cap.router, include_in_schema=False)
app.include_router(portfolio.router, include_in_schema=False)
app.include_router(documents.router, include_in_schema=False)


@app.get("/", include_in_schema=False)
def root_redirect():
    """
    Root endpoint redirect to Swagger documentation.
    """
    return {
        "title": "Nifty 100 Financial Intelligence Platform API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health_check": "/api/v1/health",
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """
    Favicon endpoint returning 204 No Content to suppress browser 404 warnings.
    """
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["src"],
    )
