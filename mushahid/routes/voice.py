"""
POST /api/voice/synthesize — turn a synthetic co-traveller's chat message
into an MP3 served from Firebase Storage.

Flow:
  1. Auth via verify_token (matches every other protected route).
  2. Look up the persona by profile_id to get their voice_id.
  3. Hash the text — same text from same persona always lands at the same
     Storage path, so re-plays are free.
  4. Check Firebase Storage for an existing MP3 at that path; if it's
     there, return the public URL without calling ElevenLabs.
  5. On cache miss: call ElevenLabs, upload to Firebase Storage, return
     the new public URL.

Cost shape: ElevenLabs charges per character on the input text. Cached
hits cost $0. First playback of a unique message costs ~$0.001-0.003.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ali.voice.elevenlabs import synthesize, ElevenLabsError
from mushahid.auth import verify_token
from mushahid.realtime.storage import _get_bucket, upload_audio_clip
from mushahid.utils.sanitize import sanitize_user_input
from shreyas.retrieval.search import get_cotraveller_by_id

router = APIRouter()
logger = logging.getLogger(__name__)

# Cap synthesizable text length — chat messages over this are almost
# always a paste, and the synth would be expensive + slow without adding
# real value. Truncate-with-ellipsis is friendlier than rejecting.
_MAX_TEXT_CHARS = 600


class SynthRequest(BaseModel):
    profile_id: str = Field(..., min_length=1, max_length=128)
    text:       str = Field(..., min_length=1)


class SynthResponse(BaseModel):
    audio_url: str
    cached:    bool
    voice_id:  str


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]


def _audio_path(profile_id: str, message_hash: str) -> str:
    return f"synthetic_audio/{profile_id}/{message_hash}.mp3"


async def _existing_url(path: str) -> str | None:
    """Return the public URL if the blob already exists, else None.
    Wrapped in to_thread because firebase_admin storage calls are sync."""
    def _check():
        bucket = _get_bucket()
        blob = bucket.blob(path)
        if not blob.exists():
            return None
        # blob.public_url is fine when make_public was called; for safety
        # we re-publish on cache check (idempotent + cheap).
        try:
            blob.make_public()
        except Exception:
            pass
        return blob.public_url
    try:
        return await asyncio.to_thread(_check)
    except Exception as e:
        logger.warning("storage existence check failed for %s: %s", path, e)
        return None


@router.post("/voice/synthesize", response_model=SynthResponse)
async def synthesize_voice(body: SynthRequest, uid: str = Depends(verify_token)):
    """Synthesize one chat message from one synthetic persona.

    Returns the public Firebase Storage URL the frontend can drop into
    an <audio> element. Identical text from the same persona is served
    from cache.
    """
    text = sanitize_user_input(body.text)[:_MAX_TEXT_CHARS]
    if not text.strip():
        raise HTTPException(400, "text is empty after sanitization")

    persona = await get_cotraveller_by_id(body.profile_id)
    if persona is None:
        raise HTTPException(404, f"co-traveller {body.profile_id} not found")
    voice_id = persona.voice_id
    if not voice_id:
        raise HTTPException(409, f"co-traveller {body.profile_id} has no voice_id")

    msg_hash = _text_hash(text)
    path     = _audio_path(body.profile_id, msg_hash)

    cached_url = await _existing_url(path)
    if cached_url:
        return SynthResponse(audio_url=cached_url, cached=True, voice_id=voice_id)

    try:
        mp3 = await synthesize(text, voice_id)
    except ElevenLabsError as e:
        logger.warning("ElevenLabs synth failed for %s: %s", body.profile_id, e)
        raise HTTPException(502, f"voice synthesis failed: {e}")

    try:
        audio_url = await upload_audio_clip(body.profile_id, msg_hash, mp3)
    except Exception as e:
        logger.warning("Firebase audio upload failed for %s: %s", path, e)
        raise HTTPException(502, f"audio storage upload failed: {e}")

    return SynthResponse(audio_url=audio_url, cached=False, voice_id=voice_id)
