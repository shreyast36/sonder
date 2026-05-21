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

# LLM providers
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

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

# App
LOCAL_MODE = os.getenv("LOCAL_MODE", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MAX_REFINEMENT_ATTEMPTS = int(os.getenv("MAX_REFINEMENT_ATTEMPTS", "3"))

# Currency conversion — optional; falls back to static rates in shared/currency.py if unset
EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY")

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
