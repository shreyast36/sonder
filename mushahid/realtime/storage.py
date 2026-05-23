"""
Firebase Storage helper for binary blobs (synthetic avatars + audio cache).

Separate module from firestore.py because the two services have different
init shapes — firebase_admin.storage requires the bucket name at App init
time, and we don't want to retrofit firestore.py's get_db() to thread
that through.

Bucket name comes from FIREBASE_STORAGE_BUCKET env var (defaults to
"{project_id}.appspot.com" if unset and FIREBASE_PROJECT_ID is set).

All uploads are public-read so the frontend can render the URLs directly
without auth — these are synthetic personas, not user content. If we
ever serve user avatars from the same bucket, switch the ACL to
authenticated-read and signed URLs.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from shared.config import (
    FIREBASE_PROJECT_ID, FIREBASE_PRIVATE_KEY, FIREBASE_CLIENT_EMAIL,
    FIREBASE_STORAGE_BUCKET, LOCAL_MODE,
)

logger = logging.getLogger(__name__)


def _bucket_name() -> str:
    if FIREBASE_STORAGE_BUCKET:
        return FIREBASE_STORAGE_BUCKET
    if FIREBASE_PROJECT_ID:
        # Best-effort default — newer Firebase projects use
        # "{project}.firebasestorage.app", legacy use "{project}.appspot.com".
        return f"{FIREBASE_PROJECT_ID}.appspot.com"
    raise RuntimeError(
        "FIREBASE_STORAGE_BUCKET is not set and FIREBASE_PROJECT_ID is "
        "missing — cannot resolve a Storage bucket."
    )


_initialized = False


def _ensure_app():
    """Initialise firebase_admin with the storage bucket name. Idempotent —
    safe to call after firestore.get_db() has already initialised the app
    (firebase_admin.initialize_app raises if called twice, so we check
    _apps first)."""
    global _initialized
    if _initialized:
        return
    import firebase_admin
    from firebase_admin import credentials
    if not firebase_admin._apps:
        cred = credentials.Certificate({
            "type":        "service_account",
            "project_id":  FIREBASE_PROJECT_ID,
            "private_key": FIREBASE_PRIVATE_KEY,
            "client_email": FIREBASE_CLIENT_EMAIL,
            "token_uri":   "https://oauth2.googleapis.com/token",
        })
        firebase_admin.initialize_app(cred, {"storageBucket": _bucket_name()})
    else:
        # An existing app was initialised (probably by firestore.py) without
        # a storageBucket option. firebase_admin doesn't let us patch the
        # default app's options after the fact, so we name the bucket
        # explicitly on every storage.bucket() call below.
        pass
    _initialized = True


def _get_bucket():
    _ensure_app()
    from firebase_admin import storage
    return storage.bucket(name=_bucket_name())


async def upload_bytes(
    path: str,
    data: bytes,
    *,
    content_type: str,
    make_public: bool = True,
) -> str:
    """Upload `data` to `path` in the configured bucket. Returns the
    publicly-accessible URL (when make_public=True) or the gs:// URI
    (when make_public=False, for private content).

    LOCAL_MODE short-circuit: writes to ./seed_assets/storage/{path}
    locally and returns a relative URL. Lets `seed_cotravellers.py --dry-run`
    iterate without hitting Firebase.
    """
    if LOCAL_MODE:
        local_path = Path("seed_assets") / "storage" / path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)
        return f"/seed_assets/storage/{path}"

    def _do_upload() -> str:
        bucket = _get_bucket()
        blob = bucket.blob(path)
        blob.upload_from_string(data, content_type=content_type)
        if make_public:
            blob.make_public()
            return blob.public_url
        return f"gs://{bucket.name}/{path}"

    try:
        return await asyncio.to_thread(_do_upload)
    except Exception as e:
        logger.warning("Firebase Storage upload failed for %s: %s", path, e)
        raise


async def upload_avatar(profile_id: str, png_bytes: bytes) -> str:
    """Convenience wrapper for synthetic co-traveller portraits."""
    return await upload_bytes(
        f"cotraveller_avatars/{profile_id}.png",
        png_bytes,
        content_type="image/png",
        make_public=True,
    )


async def upload_audio_clip(profile_id: str, message_hash: str, mp3_bytes: bytes) -> str:
    """Convenience wrapper for cached synthetic chat-reply audio.

    Same message hash from the same persona → same path → idempotent re-uploads
    (Firebase Storage overwrites by default). Used by the future audio
    playback path to avoid paying ElevenLabs per playback.
    """
    return await upload_bytes(
        f"synthetic_audio/{profile_id}/{message_hash}.mp3",
        mp3_bytes,
        content_type="audio/mpeg",
        make_public=True,
    )
