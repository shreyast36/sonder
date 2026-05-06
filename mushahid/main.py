from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO: on startup — initialise Firestore client, Sentry, PostHog
    yield
    # TODO: on shutdown — close any open connections


app = FastAPI(title="Sonder API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict to Vercel frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TODO: import and register all routers
# from mushahid.routes import plan_trip, update_trip, cotraveller, chat, health, visa
# app.include_router(plan_trip.router)
# app.include_router(update_trip.router)
# app.include_router(cotraveller.router)
# app.include_router(chat.router)
# app.include_router(health.router)
# app.include_router(visa.router)

# Run with: uvicorn mushahid.main:app --reload --port 8000
