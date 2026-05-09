from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from mushahid.auth import verify_token
from mushahid.realtime.firestore import create_user_profile, get_db
from shared.config import LOCAL_MODE

router = APIRouter()

_local_profiles: dict = {}


class CreateProfileRequest(BaseModel):
    display_name: str


@router.post("/users/profile", status_code=201)
async def create_profile(body: CreateProfileRequest, uid: str = Depends(verify_token)):
    if LOCAL_MODE:
        if uid in _local_profiles:
            return {"user_id": uid, "display_name": _local_profiles[uid], "created": False}
        _local_profiles[uid] = body.display_name
        await create_user_profile(uid, body.display_name)
        return {"user_id": uid, "display_name": body.display_name, "created": True}

    db = get_db()
    doc = db.collection("user_profiles").document(uid).get()
    if doc.exists:
        return {"user_id": uid, "display_name": doc.to_dict().get("display_name"), "created": False}
    await create_user_profile(uid, body.display_name)
    return {"user_id": uid, "display_name": body.display_name, "created": True}


@router.get("/users/profile")
async def get_profile(uid: str = Depends(verify_token)):
    if LOCAL_MODE:
        if uid not in _local_profiles:
            raise HTTPException(status_code=404, detail="Profile not found")
        return {"user_id": uid, "display_name": _local_profiles[uid]}

    db = get_db()
    doc = db.collection("user_profiles").document(uid).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Profile not found")
    return doc.to_dict()
