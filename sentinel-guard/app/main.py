from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import v1_router

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_DEFAULT])


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Professional security scanning API. "
        "All scans run exclusively on verified, owned assets."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = settings.cors_origins_list()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PUT", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

allowed_hosts = settings.allowed_hosts_list()
if allowed_hosts != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

app.include_router(v1_router, prefix="/api")


@app.get("/health", tags=["Health"])
async def health(request: Request):
    return {"status": "ok", "version": settings.APP_VERSION}
