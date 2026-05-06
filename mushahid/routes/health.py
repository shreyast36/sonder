from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Service health check. Used by Render's health check configuration.

    Expected output:
        {
            "status": "healthy",
            "services": {
                "api":       "up",
                "firestore": "up",
                "pinecone":  "up"
            }
        }

    If any service is unreachable, return status "degraded" with the failing service marked "down".
    """
    # TODO: ping Firestore and Pinecone, return status dict
    return {"status": "ok"}
