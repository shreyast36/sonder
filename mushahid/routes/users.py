import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from mushahid.auth import verify_token
from mushahid.realtime.firestore import create_user_profile, get_db
from mushahid.utils.sanitize import sanitize_user_input
from shared.config import LOCAL_MODE

router = APIRouter()
logger = logging.getLogger(__name__)

_local_profiles: dict = {}


class CreateProfileRequest(BaseModel):
    display_name: str


@router.post("/users/profile", status_code=201)
async def create_profile(body: CreateProfileRequest, uid: str = Depends(verify_token)):
    display_name = sanitize_user_input(body.display_name)
    if LOCAL_MODE:
        if uid in _local_profiles:
            return {"user_id": uid, "display_name": _local_profiles[uid], "created": False}
        _local_profiles[uid] = display_name
        await create_user_profile(uid, display_name)
        return {"user_id": uid, "display_name": display_name, "created": True}

    try:
        db = get_db()
        doc = db.collection("user_profiles").document(uid).get()
        if doc.exists:
            return {"user_id": uid, "display_name": doc.to_dict().get("display_name"), "created": False}
        await create_user_profile(uid, display_name)
        return {"user_id": uid, "display_name": display_name, "created": True}
    except Exception as e:
        logger.warning("create_profile Firestore call failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e


@router.get("/users/profile")
async def get_profile(uid: str = Depends(verify_token)):
    if LOCAL_MODE:
        if uid not in _local_profiles:
            raise HTTPException(status_code=404, detail="Profile not found")
        return {"user_id": uid, "display_name": _local_profiles[uid]}

    try:
        db = get_db()
        doc = db.collection("user_profiles").document(uid).get()
    except Exception as e:
        logger.warning("get_profile Firestore call failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Profile not found")
    return doc.to_dict()
