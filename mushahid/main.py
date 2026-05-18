import logging
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

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=0.2,
        send_default_pii=False,
    )

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

## temporary test route for sentry
@app.get("/debug-sentry")
async def trigger_error():
    raise Exception("This is a test exception, sentry should capture this!")

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
