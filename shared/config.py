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
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# Model selection — Ali decides these values
SMALL_MODEL_PROVIDER = os.getenv("SMALL_MODEL_PROVIDER")
SMALL_MODEL_NAME = os.getenv("SMALL_MODEL_NAME")
LARGE_MODEL_PROVIDER = os.getenv("LARGE_MODEL_PROVIDER")
LARGE_MODEL_NAME = os.getenv("LARGE_MODEL_NAME")
VALIDATOR_MODEL_PROVIDER = os.getenv("VALIDATOR_MODEL_PROVIDER")
VALIDATOR_MODEL_NAME = os.getenv("VALIDATOR_MODEL_NAME")

# Embeddings — Shreyas decides provider and model
EMBED_MODEL_PROVIDER = os.getenv("EMBED_MODEL_PROVIDER")   # openai | bedrock | (others)
EMBED_MODEL = os.getenv("EMBED_MODEL")                     # model name / ID within that provider
EMBED_DIMENSIONS = int(os.getenv("EMBED_DIMENSIONS", "1536"))

# Pinecone
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east-1-aws")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "sonder-index")

# AWS — used when any provider is set to "bedrock", or for ECS deployment
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")         # not needed on ECS (uses IAM role)
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY") # not needed on ECS (uses IAM role)

# Bedrock model IDs — Ali decides these values
# Set whichever tiers you route to Bedrock; leave blank if using a different provider for that tier
BEDROCK_SMALL_MODEL_ID = os.getenv("BEDROCK_SMALL_MODEL_ID")
BEDROCK_LARGE_MODEL_ID = os.getenv("BEDROCK_LARGE_MODEL_ID")
BEDROCK_VALIDATOR_MODEL_ID = os.getenv("BEDROCK_VALIDATOR_MODEL_ID")
BEDROCK_EMBED_MODEL_ID = os.getenv("BEDROCK_EMBED_MODEL_ID")  # Shreyas: set if EMBED_MODEL_PROVIDER=bedrock

# Redis — required in production (ECS multi-container) for Shreyas's ConnectionManager
# Provided by ElastiCache; ignored when LOCAL_MODE=true (in-memory fallback is fine locally)
REDIS_URL = os.getenv("REDIS_URL")

# App
LOCAL_MODE = os.getenv("LOCAL_MODE", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MAX_REFINEMENT_ATTEMPTS = int(os.getenv("MAX_REFINEMENT_ATTEMPTS", "3"))

# Monitoring
SENTRY_DSN = os.getenv("SENTRY_DSN")
POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY")
