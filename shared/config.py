# Maintained by Jahnvi — all environment variables are read here.
# Every module imports from this file. Never call os.getenv() elsewhere.

from dotenv import load_dotenv
import os

load_dotenv()

# Firebase
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_PRIVATE_KEY = os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n")
FIREBASE_CLIENT_EMAIL = os.getenv("FIREBASE_CLIENT_EMAIL")

# LLM providers
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# LLM model selection — Ali decides Small + Large; Mushahid decides validators
SMALL_MODEL_PROVIDER = os.getenv("SMALL_MODEL_PROVIDER")
SMALL_MODEL_NAME     = os.getenv("SMALL_MODEL_NAME")
LARGE_MODEL_PROVIDER = os.getenv("LARGE_MODEL_PROVIDER")
LARGE_MODEL_NAME     = os.getenv("LARGE_MODEL_NAME")

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

# CORS — comma-separated list of allowed frontend origins
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")]

# Rate limiting — max /plan-trip calls per user per window
PLAN_TRIP_RATE_LIMIT = os.getenv("PLAN_TRIP_RATE_LIMIT", "5/hour")

# Monitoring
SENTRY_DSN = os.getenv("SENTRY_DSN")
POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY")
