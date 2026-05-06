from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class CreateProfileRequest(BaseModel):
    display_name: str


@router.post("/users/profile", status_code=201)
async def create_user_profile(body: CreateProfileRequest):
    """
    Create a UserProfile document in Firestore on first sign-in.
    Call this once immediately after Firebase Auth creates the account — before
    the user reaches Screen 2. Every other endpoint assumes the profile exists.

    Auth: requires Firebase ID token (user_id extracted from the verified token).

    Expected input:
        Authorization: Bearer <firebase_id_token>
        { "display_name": "Arjun" }

    Expected output:
        { "user_id": "firebase_uid_abc123", "display_name": "Arjun", "created": true }

    Idempotent: if the profile already exists, return 200 without overwriting.
    """
    # TODO: user_id = verify_token(authorization header)
    # TODO: check if user_profiles/{user_id} already exists — return 200 if so
    # TODO: await create_user_profile(user_id, body.display_name)
    # TODO: return {"user_id": user_id, "display_name": body.display_name, "created": True}
    raise NotImplementedError


@router.get("/users/profile")
async def get_user_profile():
    """
    Fetch the current user's profile from Firestore.

    Auth: requires Firebase ID token.

    Expected output: UserProfile as JSON, or 404 if profile not yet created.
    """
    # TODO: user_id = verify_token(authorization header)
    # TODO: return get_db().collection("user_profiles").document(user_id).get()
    raise NotImplementedError
