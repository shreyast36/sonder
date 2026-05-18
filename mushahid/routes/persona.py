"""
POST /api/persona-infer — runs HF embedding + cosine vs the 12 dimension
prototypes, then renders the deterministic reveal copy. Called by the
frontend right after the user finishes the persona screens, before any
itinerary generation.
"""

import asyncio
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from mushahid.auth import verify_token
from mushahid.utils.sanitize import sanitize_user_input
from shared.schemas import TripConstraints, PersonaQuestionAnswers
from jahnvi.pipeline.module3_persona import infer_persona
from jahnvi.data.persona_copy import (
    descriptor, paragraph, bullets_from_keys, SOFTENER,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class PersonaInferRequest(BaseModel):
    constraints:     TripConstraints
    persona_answers: PersonaQuestionAnswers


class PersonaInferResponse(BaseModel):
    softener:      str
    descriptor:    str
    paragraph:     str
    bullets:       list[str]
    top_push:      list[str]
    top_interests: list[str]
    pace:          str
    user_vector:   list[float]


@router.post("/persona-infer", response_model=PersonaInferResponse)
async def persona_infer(
    body: PersonaInferRequest,
    uid: str = Depends(verify_token),
) -> PersonaInferResponse:
    # Sanitize free-text fields before they hit the embedder.
    answers = body.persona_answers.model_copy(update={
        "small_thing": sanitize_user_input(body.persona_answers.small_thing or ""),
    })

    # infer_persona is sync (calls the HF model). Run in a thread so we don't
    # block the event loop while the encoder does its work.
    persona = await asyncio.to_thread(infer_persona, body.constraints, answers)

    # Compose the reveal copy. All deterministic — no LLM.
    bullet_keys = [
        body.constraints.friends_would_say,
        body.constraints.restaurant_order,
        body.constraints.what_you_notice,
        body.constraints.ideal_atmosphere,
    ]
    bullets = bullets_from_keys(bullet_keys)

    top_push      = persona["top_push"]
    top_interests = persona["top_interests"]

    return PersonaInferResponse(
        softener      = SOFTENER,
        descriptor    = descriptor(top_push[0] if top_push else None,
                                   top_interests[0] if top_interests else None),
        paragraph     = paragraph(top_push[0] if top_push else None),
        bullets       = bullets,
        top_push      = top_push,
        top_interests = top_interests,
        pace          = persona["pace"],
        user_vector   = persona["user_vector"],
    )
