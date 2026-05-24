# Maintained by Jahnvi — all environment variables are read here.
# Every module imports from this file. Never call os.getenv() elsewhere.

from dotenv import load_dotenv
import os

load_dotenv()

# Firebase
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_PRIVATE_KEY = os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n")
FIREBASE_CLIENT_EMAIL = os.getenv("FIREBASE_CLIENT_EMAIL")
FIRESTORE_DATABASE_ID = os.getenv("FIRESTORE_DATABASE_ID")  # None → "(default)"; set if using a named DB
# Firebase Storage bucket — e.g. "your-project.appspot.com" or "your-project.firebasestorage.app".
# Required for synthetic avatar uploads + future audio caching. Mirror of VITE_FIREBASE_STORAGE_BUCKET
# on the frontend.
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")

# LLM providers
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

# ElevenLabs — TTS for synthetic co-traveller voice playback.
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
# Model id passed to ElevenLabs. Multilingual v2 handles non-English accents
# for personas from non-English cities (Mumbai, Tokyo, Lisbon, etc.).
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

# LLM model selection — Ali decides Small + Large; Mushahid decides validators
# *_MODEL_PROVIDER picks the primary provider for the tier. The engine still
# falls back to the other provider on failure, but each client now uses its
# OWN model name (not the primary's) so the fallback can't accidentally send
# an Anthropic model id to OpenAI or vice-versa.
SMALL_MODEL_PROVIDER = os.getenv("SMALL_MODEL_PROVIDER")
LARGE_MODEL_PROVIDER = os.getenv("LARGE_MODEL_PROVIDER")

# Legacy single-name vars — kept so existing .env files don't break. Used as
# a tier-wide default when the provider-specific var isn't set AND the
# legacy provider matches.
SMALL_MODEL_NAME = os.getenv("SMALL_MODEL_NAME")
LARGE_MODEL_NAME = os.getenv("LARGE_MODEL_NAME")

def _per_provider_model(env_var: str, provider: str, fallback: str) -> str:
    """Resolve a per-provider model name. Order of precedence:
    1. The dedicated env var (e.g. ANTHROPIC_SMALL_MODEL).
    2. Legacy {TIER}_MODEL_NAME — only if {TIER}_MODEL_PROVIDER matches.
    3. Hardcoded sensible default for the provider/tier."""
    v = os.getenv(env_var)
    if v:
        return v
    legacy_provider = SMALL_MODEL_PROVIDER if "SMALL" in env_var else LARGE_MODEL_PROVIDER
    legacy_name     = SMALL_MODEL_NAME     if "SMALL" in env_var else LARGE_MODEL_NAME
    if legacy_name and legacy_provider == provider:
        return legacy_name
    return fallback

# Per-provider model ids — clients read these directly, so a fallback from
# the primary to the alternate provider always sends a valid id.
ANTHROPIC_SMALL_MODEL = _per_provider_model("ANTHROPIC_SMALL_MODEL", "anthropic", "claude-haiku-4-5-20251001")
ANTHROPIC_LARGE_MODEL = _per_provider_model("ANTHROPIC_LARGE_MODEL", "anthropic", "claude-sonnet-4-6")
OPENAI_SMALL_MODEL    = _per_provider_model("OPENAI_SMALL_MODEL",    "openai",    "gpt-4o-mini")
OPENAI_LARGE_MODEL    = _per_provider_model("OPENAI_LARGE_MODEL",    "openai",    "gpt-4o")

# Validator LLMs — Mushahid owns these (called directly from validation/critic.py)
SMALL_VALIDATOR_PROVIDER   = os.getenv("SMALL_VALIDATOR_PROVIDER")
SMALL_VALIDATOR_MODEL_NAME = os.getenv("SMALL_VALIDATOR_MODEL_NAME")
LARGE_VALIDATOR_PROVIDER   = os.getenv("LARGE_VALIDATOR_PROVIDER")
LARGE_VALIDATOR_MODEL_NAME = os.getenv("LARGE_VALIDATOR_MODEL_NAME")

# Embeddings — Ali decides provider and model
EMBED_MODEL_PROVIDER = os.getenv("EMBED_MODEL_PROVIDER")
EMBED_MODEL          = os.getenv("EMBED_MODEL")
EMBED_DIMENSIONS     = int(os.getenv("EMBED_DIMENSIONS", "1536"))

# Pinecone
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east-1-aws")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "sonder-index")

# AWS — used when any provider is set to "bedrock", or for ECS deployment
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")         # not needed on ECS (uses IAM role)
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY") # not needed on ECS (uses IAM role)

# Bedrock model IDs — only needed when the relevant provider is set to "bedrock"
BEDROCK_SMALL_MODEL_ID           = os.getenv("BEDROCK_SMALL_MODEL_ID")
BEDROCK_LARGE_MODEL_ID           = os.getenv("BEDROCK_LARGE_MODEL_ID")
BEDROCK_SMALL_VALIDATOR_MODEL_ID = os.getenv("BEDROCK_SMALL_VALIDATOR_MODEL_ID")
BEDROCK_LARGE_VALIDATOR_MODEL_ID = os.getenv("BEDROCK_LARGE_VALIDATOR_MODEL_ID")
BEDROCK_EMBED_MODEL_ID           = os.getenv("BEDROCK_EMBED_MODEL_ID")

# Redis — required in production (ECS multi-container) for Shreyas's ConnectionManager
# Provided by ElastiCache; ignored when LOCAL_MODE=true (in-memory fallback is fine locally)
REDIS_URL = os.getenv("REDIS_URL")

# Presence TTL — users are considered offline if no heartbeat within this window
PRESENCE_TTL_SECONDS = int(os.getenv("PRESENCE_TTL_SECONDS", "90"))

# Ranking policy version — picks which set of policy modules under
# shreyas/ranking/policies/ the engine loads. V1 ships uniform-weight
# priors; future versions can co-exist (e.g. cotraveller_v2.py) and an
# env-var flip switches surfaces between them for A/B testing without
# code changes.
RANKING_POLICY_VERSION = os.getenv("RANKING_POLICY_VERSION", "v1")

# App
LOCAL_MODE = os.getenv("LOCAL_MODE", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MAX_REFINEMENT_ATTEMPTS = int(os.getenv("MAX_REFINEMENT_ATTEMPTS", "3"))

# Background loop that drives synthetic personas to post on the social
# feed and open trips on /discover at randomised intervals so the
# surfaces feel populated even with no other real users online.
# Disable in test/CI runs and on prod environments where real activity
# would be unhelpful or expensive.
SYNTHETIC_AGENTS_ENABLED       = os.getenv("SYNTHETIC_AGENTS_ENABLED", "true").lower() == "true"
# Aggressive cadence: real users feel the surface as "alive" rather than
# "auto-populated every couple of minutes". Tunable downward (cost) or
# upward (feel) via env.
SYNTHETIC_AGENTS_MIN_INTERVAL  = int(os.getenv("SYNTHETIC_AGENTS_MIN_INTERVAL", "8"))
SYNTHETIC_AGENTS_MAX_INTERVAL  = int(os.getenv("SYNTHETIC_AGENTS_MAX_INTERVAL", "25"))
# How many actions to fire in parallel on cold-start so the feed isn't
# empty when the first real user lands. 0 = don't seed.
SYNTHETIC_AGENTS_SEED_COUNT    = int(os.getenv("SYNTHETIC_AGENTS_SEED_COUNT", "6"))

# Currency conversion — optional; falls back to static rates in shared/currency.py if unset
EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY")

# Pixabay — free travel-photo API used to auto-illustrate social posts
# and trip-recap cards. Get a key at https://pixabay.com/api/docs/
# (free tier: 100 req/min, 5000 req/hour). When unset, posts render
# without images and synthetic agents skip the image fetch silently.
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")

# Email — transactional itinerary delivery
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "resend")  # resend | sendgrid | ses
EMAIL_API_KEY  = os.getenv("EMAIL_API_KEY")
EMAIL_FROM     = os.getenv("EMAIL_FROM", "itinerary@sonder.app")

# Web Push (VAPID) — closed-browser push notifications via service worker.
# Generate once with `python -m scripts.generate_vapid_keys` and paste both
# halves into the env. If unset, the backend silently skips web push and only
# the in-app banner / Notification-API fallback fires.
VAPID_PUBLIC_KEY  = os.getenv("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
# 'sub' claim sent to push services — mailto: address the push provider can
# reach if your traffic looks abusive. Use a real ops mailbox in prod.
VAPID_SUBJECT     = os.getenv("VAPID_SUBJECT", "mailto:ops@sonder.app")

# CORS — comma-separated list of allowed frontend origins
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176,http://localhost:5177,http://localhost:5178,http://localhost:5179").split(",")]

# Rate limiting — max calls per user per window
PLAN_TRIP_RATE_LIMIT = os.getenv("PLAN_TRIP_RATE_LIMIT", "5/hour")
UPDATE_TRIP_RATE_LIMIT = os.getenv("UPDATE_TRIP_RATE_LIMIT", "20/hour")

# Monitoring
SENTRY_DSN = os.getenv("SENTRY_DSN")
POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY")
# US cloud is https://us.i.posthog.com (default), EU is https://eu.i.posthog.com.
# Self-hosters set their own URL. Mismatched region = silent event drops.
POSTHOG_HOST = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com")
