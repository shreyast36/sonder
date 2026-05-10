import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from shared.config import ALLOWED_ORIGINS, LOCAL_MODE, FIREBASE_PROJECT_ID

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
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from mushahid.routes import plan_trip, update_trip, cotraveller, chat, users, visa, export, health

app.include_router(health.router)
app.include_router(visa.router)
app.include_router(users.router)
app.include_router(plan_trip.router)
app.include_router(update_trip.router)
app.include_router(cotraveller.router)
app.include_router(chat.router)
app.include_router(export.router)
