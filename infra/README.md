# Sonder — AWS Infrastructure

This folder contains infrastructure config for running Sonder on AWS. Local development does not require any of this — everything runs on `localhost` with `.env` values.

---

## Architecture Overview

```
                         ┌─────────────────────────────────┐
  Browser / Mobile       │           AWS Cloud              │
  ─────────────────      │                                   │
  React (Vercel)  ───────┼──► CloudFront ──► ALB            │
                         │                    │              │
                         │                    ▼              │
                         │            ECS Fargate            │
                         │          (sonder-backend)         │
                         │           FastAPI :8000           │
                         │                    │              │
                         │         ┌──────────┼──────────┐   │
                         │         │          │          │   │
                         │         ▼          ▼          ▼   │
                         │   AWS Bedrock  Pinecone   Firebase │
                         │  (LLM calls)  (vectors)  (auth +  │
                         │               ─ stays ─   Firestore│
                         │               external)  ─ stays ─│
                         │                                   │
                         │   ElastiCache    Secrets    Cloud  │
                         │     Redis       Manager    Watch   │
                         │  (WebSocket    (all keys)  (logs)  │
                         │   sessions)                        │
                         └─────────────────────────────────┘
```

---

## Components

### ECS Fargate — FastAPI backend
- Replaces Render for production.
- Fargate handles auto-scaling with no instance management.
- Supports long-lived SSE connections and persistent WebSocket connections — Render's free tier drops these under load.
- Start command: `uvicorn mushahid.main:app --host 0.0.0.0 --port 8000`
- Task definition: `infra/ecs-task-definition.json` (replace all `<ACCOUNT_ID>` and `<AWS_REGION>` placeholders before deploying)

### AWS Bedrock — LLM inference
- Ali: set `LARGE_MODEL_PROVIDER=bedrock`, `SMALL_MODEL_PROVIDER=bedrock`, or `VALIDATOR_MODEL_PROVIDER=bedrock` (any combination).
- The `BedrockLargeClient`, `BedrockSmallClient`, `BedrockValidatorClient` in `ali/clients/bedrock_client.py` call `bedrock-runtime` via `boto3`.
- On ECS, no `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` needed — the task IAM role (`sonderTaskRole`) handles auth. Locally you need credentials in `.env` or `~/.aws/credentials`.
- The IAM task role must have `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` permissions.

### Pinecone — vector database (unchanged)
- Shreyas's retrieval layer talks directly to Pinecone via `PINECONE_API_KEY`.
- Nothing about Pinecone changes in production — it is already a managed cloud service.
- Shreyas: if you set `EMBED_MODEL_PROVIDER=bedrock`, your embedding calls go via `bedrock-runtime` but vectors still go into Pinecone as normal.

### ElastiCache Redis — WebSocket session state
- Shreyas: your `ConnectionManager` in `cotraveller/chat.py` currently stores sessions in a Python dict.
- **This breaks in production** — ECS runs multiple container instances, and a WebSocket connection could land on a different container than the one holding the session dict.
- Fix: replace the in-memory dict with Redis pub/sub. Each container subscribes to the session channel; messages broadcast via Redis reach all containers.
- `REDIS_URL` is read from `shared/config.py`. When `LOCAL_MODE=true` the in-memory fallback is fine.
- Suggested approach: `aioredis` + pub/sub per `session_id`.

### AWS Secrets Manager — all API keys
- Every secret in `.env.example` has a corresponding entry pulled from Secrets Manager in `ecs-task-definition.json`.
- Secrets are organised into groups: `sonder/firebase`, `sonder/pinecone`, `sonder/llm`, `sonder/models`, `sonder/redis`, `sonder/monitoring`.
- The ECS execution role (`ecsTaskExecutionRole`) must have `secretsmanager:GetSecretValue` permission on all `sonder/*` secrets.
- Locally: keep using `.env` — `shared/config.py` calls `load_dotenv()` first.

### CloudWatch — logs and metrics
- All container stdout/stderr goes to `/ecs/sonder-backend` log group automatically via the `awslogs` driver (already configured in the task definition).
- Recommended: create a CloudWatch dashboard with:
  - p95 latency per route (ALB access logs → metric filter)
  - `itinerary_generation` token usage (log the token count in `ali/generation/itinerary_generator.py`)
  - Refinement loop attempts (log in `mushahid/refinement/loop.py`)

---

## Deployment Steps

### One-time setup

```bash
# 1. Create ECR repository
aws ecr create-repository --repository-name sonder-backend --region <AWS_REGION>

# 2. Create CloudWatch log group
aws logs create-log-group --log-group-name /ecs/sonder-backend --region <AWS_REGION>

# 3. Create Secrets Manager secrets (do this for every key in .env.example)
aws secretsmanager create-secret --name sonder/firebase --secret-string '{"FIREBASE_PROJECT_ID":"...","FIREBASE_PRIVATE_KEY":"...","FIREBASE_CLIENT_EMAIL":"..."}'
aws secretsmanager create-secret --name sonder/pinecone --secret-string '{"PINECONE_API_KEY":"...","PINECONE_INDEX_NAME":"sonder-index"}'
aws secretsmanager create-secret --name sonder/llm     --secret-string '{"OPENAI_API_KEY":"...","ANTHROPIC_API_KEY":"...","GOOGLE_API_KEY":"...","GROQ_API_KEY":"...","MISTRAL_API_KEY":"..."}' # include only the keys for providers Ali selects
aws secretsmanager create-secret --name sonder/models  --secret-string '{"SMALL_MODEL_PROVIDER":"...","SMALL_MODEL_NAME":"...","LARGE_MODEL_PROVIDER":"...","LARGE_MODEL_NAME":"...","VALIDATOR_MODEL_PROVIDER":"...","VALIDATOR_MODEL_NAME":"...","BEDROCK_SMALL_MODEL_ID":"...","BEDROCK_LARGE_MODEL_ID":"...","BEDROCK_VALIDATOR_MODEL_ID":"...","EMBED_MODEL_PROVIDER":"...","EMBED_MODEL":"...","EMBED_DIMENSIONS":"1536","BEDROCK_EMBED_MODEL_ID":"..."}'
aws secretsmanager create-secret --name sonder/redis   --secret-string '{"REDIS_URL":"redis://..."}'

# 4. Create IAM roles
#    ecsTaskExecutionRole — needs AmazonECSTaskExecutionRolePolicy + secretsmanager:GetSecretValue
#    sonderTaskRole        — needs bedrock:InvokeModel + bedrock:InvokeModelWithResponseStream

# 5. Create ECS cluster
aws ecs create-cluster --cluster-name sonder --region <AWS_REGION>

# 6. Register task definition (after replacing placeholders in ecs-task-definition.json)
aws ecs register-task-definition --cli-input-json file://infra/ecs-task-definition.json
```

### Deploy a new image

```bash
# Build and push
docker build -t sonder-backend .
aws ecr get-login-password --region <AWS_REGION> | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com
docker tag sonder-backend:latest <ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/sonder-backend:latest
docker push <ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/sonder-backend:latest

# Force ECS to pull the new image
aws ecs update-service --cluster sonder --service sonder-backend --force-new-deployment
```

### Frontend (Vercel — unchanged)
Update `VITE_API_BASE_URL` in Vercel environment variables to point to your ALB DNS name or CloudFront distribution URL.

---

## IAM Permissions Reference

### `sonderTaskRole` (attached to the running container)
```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream"
  ],
  "Resource": "*"
}
```

### `ecsTaskExecutionRole` (used by ECS to pull secrets + image)
- Attach managed policy: `arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy`
- Add inline policy for Secrets Manager:
```json
{
  "Effect": "Allow",
  "Action": ["secretsmanager:GetSecretValue"],
  "Resource": "arn:aws:secretsmanager:<AWS_REGION>:<ACCOUNT_ID>:secret:sonder/*"
}
```
