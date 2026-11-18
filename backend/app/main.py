import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.crypto import TemplateKeyError
from app.db import init_db
from app.face.engine import EngineUnavailable
from app.limiter import limiter
from app.routers import attendance, technicians

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="FaceAttend",
        description="Face attendance with server-verified liveness. Only encrypted face embeddings are stored.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.exception_handler(EngineUnavailable)
    @app.exception_handler(TemplateKeyError)
    async def not_configured(_request: Request, exc: Exception):
        # Missing models or encryption key: explain what to do instead of a bare 500
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origin_list,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-Admin-Key"],
    )
    app.include_router(technicians.router, prefix="/api")
    app.include_router(attendance.router, prefix="/api")

    @app.get("/api/health", tags=["health"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()
