"""
ElevenLabs TTS client.

Thin async wrapper around POST /v1/text-to-speech/{voice_id}. Returns
raw MP3 bytes. Caching + Firebase Storage upload is the caller's job
(see mushahid/routes/voice.py) so this module stays pure.

Not part of the LLM client hierarchy (ali/clients/base.py) because TTS
is a different abstraction — no model tier, no streaming text, no
fallback routing.
"""

from __future__ import annotations

import logging

import httpx

from shared.config import ELEVENLABS_API_KEY, ELEVENLABS_MODEL_ID

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

# Sensible defaults that match ElevenLabs' UI defaults. Bumping similarity
# too high makes voices monotone; stability too high makes them flat.
_DEFAULT_VOICE_SETTINGS = {
    "stability":        0.5,
    "similarity_boost": 0.75,
    "style":            0.0,
    "use_speaker_boost": True,
}


class ElevenLabsError(RuntimeError):
    """Raised when ElevenLabs returns a non-2xx response."""


async def synthesize(
    text: str,
    voice_id: str,
    *,
    model_id: str | None = None,
    voice_settings: dict | None = None,
    timeout: float = 30.0,
) -> bytes:
    """Synthesize `text` with `voice_id`, return MP3 bytes.

    Raises ElevenLabsError on auth / quota / bad-voice failures so the
    caller can decide how to surface to the user.
    """
    if not ELEVENLABS_API_KEY:
        raise ElevenLabsError("ELEVENLABS_API_KEY is not set")
    if not voice_id:
        raise ElevenLabsError("voice_id is required")
    if not text or not text.strip():
        raise ElevenLabsError("text is empty")

    body = {
        "text":           text,
        "model_id":       model_id or ELEVENLABS_MODEL_ID,
        "voice_settings": voice_settings or _DEFAULT_VOICE_SETTINGS,
    }
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "accept":     "audio/mpeg",
        "content-type": "application/json",
    }
    url = _ENDPOINT.format(voice_id=voice_id)

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=body, headers=headers)
    if resp.status_code != 200:
        # ElevenLabs returns JSON error bodies on failures.
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        logger.warning("ElevenLabs TTS failed (%d): %s", resp.status_code, detail)
        raise ElevenLabsError(f"ElevenLabs TTS failed ({resp.status_code}): {detail}")
    return resp.content
