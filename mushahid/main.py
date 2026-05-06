from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from shared.config import ALLOWED_ORIGINS, PLAN_TRIP_RATE_LIMIT


# Rate limiter — keyed by IP until auth is implemented, then switch to UID.
# Once mushahid/auth.py verify_token is working, replace with:
#   def get_user_id(request: Request) -> str:
#       token = request.headers.get("Authorization", "").replace("Bearer ", "")
#       return firebase_auth.verify_id_token(token)["uid"]
#   limiter = Limiter(key_func=get_user_id)
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO: initialise Firestore client (get_db()), Sentry, PostHog
    # TODO: start background task for presence cleanup (cleanup_stale_presence every 60s)
    yield
    # TODO: close any open connections


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

# TODO: import and register all routers once implemented
# from mushahid.routes import plan_trip, update_trip, cotraveller, chat, health, visa, users, export
# app.include_router(plan_trip.router)
# app.include_router(update_trip.router)
# app.include_router(cotraveller.router)
# app.include_router(chat.router)
# app.include_router(health.router)
# app.include_router(visa.router)
# app.include_router(users.router)
# app.include_router(export.router)

# Run with: uvicorn mushahid.main:app --reload --port 8000
