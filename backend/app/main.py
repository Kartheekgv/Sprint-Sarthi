from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router
from app.core.config import get_settings
from app.core.logging import configure_logging


configure_logging()
log = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.ensure_directories()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))[:128]
    structlog.contextvars.bind_contextvars(request_id=request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        log.info("request.completed", method=request.method, path=request.url.path, status=response.status_code)
        return response
    finally:
        structlog.contextvars.clear_contextvars()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(router, prefix=settings.api_prefix)
