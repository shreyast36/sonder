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


def scaffold_review() -> None:
    """
    Mushahid — health_check() currently returns a static dict. The task requires
    pinging Firestore and Pinecone and returning "degraded" with the failing service
    marked "down" if either is unreachable. Delete this function once real checks
    are implemented.
    """
    raise NotImplementedError
