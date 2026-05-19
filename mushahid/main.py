import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from shared.config import ALLOWED_ORIGINS, LOCAL_MODE, FIREBASE_PROJECT_ID, SENTRY_DSN

_LOCAL_DEV_ORIGINS = [f"http://localhost:{p}" for p in range(5173, 5180)]
_CORS_ORIGINS = _LOCAL_DEV_ORIGINS if LOCAL_MODE else ALLOWED_ORIGINS

import sentry_sdk
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration

def _valid_sentry_dsn(dsn: str | None) -> bool:
    # A real DSN looks like "https://<pubkey>@<host>/<project_id>".
    # Guard against the .env.example placeholder leaking into prod, which
    # would crash startup with BadDsn before any route can register.
    if not dsn:
        return False
    if not (dsn.startswith("https://") or dsn.startswith("http://")):
        return False
    if "@" not in dsn or "..." in dsn:
        return False
    return True


if _valid_sentry_dsn(SENTRY_DSN):
    # Render exposes the deploy commit as RENDER_GIT_COMMIT — use it for release
    # tracking so we can tell when a fix actually shipped vs. is still pending.
    _release = os.getenv("RENDER_GIT_COMMIT") or os.getenv("GIT_COMMIT_SHA")
    try:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[StarletteIntegration(), FastApiIntegration()],
            environment="development" if LOCAL_MODE else "production",
            release=_release,
            traces_sample_rate=0.2,
            profiles_sample_rate=0.1,
            send_default_pii=False,
        )
    except Exception as e:
        # Never let a bad Sentry DSN take the whole API down.
        print(f"[startup] Sentry init failed, continuing without it: {e}")

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if LOCAL_MODE and FIREBASE_PROJECT_ID:
        logger.critical(
            "LOCAL_MODE=true but FIREBASE_PROJECT_ID is set — "
            "Firebase authentication is DISABLED. "
            "Never run this configuration in production."
        )

    # Send one Sentry event per cold-start so the dashboard sees the first
    # event quickly (gets past the SDK-setup onboarding screen) and so each
    # deploy registers as a release in Sentry's releases view.
    if sentry_sdk.Hub.current.client:
        sentry_sdk.capture_message("Sonder backend started", level="info")

    # Env audit — log which critical vars are present (presence only, no values).
    from shared import config as cfg
    critical = [
        "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "NVIDIA_API_KEY",
        "SMALL_MODEL_PROVIDER", "SMALL_MODEL_NAME",
        "LARGE_MODEL_PROVIDER", "LARGE_MODEL_NAME",
        "SMALL_VALIDATOR_PROVIDER", "SMALL_VALIDATOR_MODEL_NAME",
        "LARGE_VALIDATOR_PROVIDER", "LARGE_VALIDATOR_MODEL_NAME",
        "EMBED_MODEL_PROVIDER", "EMBED_MODEL",
    ]
    present, missing = [], []
    for name in critical:
        val = getattr(cfg, name, None)
        (present if val else missing).append(name)
    logger.warning("ENV AUDIT — present: %s", ", ".join(present) or "(none)")
    if missing:
        logger.warning("ENV AUDIT — MISSING: %s", ", ".join(missing))

    yield


app = FastAPI(title="Sonder API", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from mushahid.routes import plan_trip, update_trip, cotraveller, chat, users, visa, export, health, persona, auth as auth_routes

app.include_router(health.router)
app.include_router(visa.router,         prefix="/api")
app.include_router(users.router,        prefix="/api")
app.include_router(auth_routes.router,  prefix="/api")
app.include_router(plan_trip.router,    prefix="/api")
app.include_router(update_trip.router,  prefix="/api")
app.include_router(persona.router,      prefix="/api")
app.include_router(cotraveller.router,  prefix="/api")
app.include_router(chat.router,         prefix="/api")
app.include_router(export.router,       prefix="/api")
