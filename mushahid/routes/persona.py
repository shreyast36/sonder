"""
POST /api/persona-infer

Two-stage inference:
  1. HF embedding + cosine vs the 12 dimension prototypes → top_push, top_interests, pace.
  2. Small LLM (Haiku via `persona_label` task type) generates the reveal copy
     (descriptor + paragraph + bullets), conditioned on top dims + the user's
     own answer labels. Falls back to deterministic copy in jahnvi/data/persona_copy.py
     if the LLM call or JSON parse fails.

The LLM never sees Pinecone, never plans a trip. Itinerary generation only
fires after the user confirms the reveal on the frontend.
"""

import asyncio
import json
import logging
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from mushahid.auth import verify_token
from mushahid.utils.sanitize import sanitize_user_input
from shared.schemas import TripConstraints, PersonaQuestionAnswers
from jahnvi.pipeline.module3_persona import infer_persona
from jahnvi.data.persona_labels import label_for
from jahnvi.data.persona_copy import (
    descriptor as fallback_descriptor,
    paragraph as fallback_paragraph,
    bullets_from_keys,
    SOFTENER,
)
from ali.routing.engine import route_request

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Request / response ────────────────────────────────────────────────────────

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


# ── Prompt scaffolding ────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You write short, observational persona summaries for a travel app's "here's who you are" reveal screen.

Voice rules:
- Low-ego, concrete nouns, slightly self-aware. Not horoscope, not MBTI, not psychometric.
- Echo the user's actual answer choices — never invent specifics they didn't say.
- Editorial register — a travel magazine writer noticing something true about a person, not a brand voice.

Return ONLY a JSON object with three keys:
- "descriptor": one short observational phrase, 4-9 words, no period. Example shapes: "Slow curiosity with hidden corners and locals' tips", "Quiet mornings, strong opinions, good food", "Restless energy chasing the right rooms".
- "paragraph": 2-3 sentences. How this person travels. Concrete. No archetype labels.
- "bullets": exactly 3 phrases (5-12 words each), no period, lowercase start. Each phrase paraphrases ONE of the user's actual answers. Example: "long dinners that turn into the whole night".

No preamble. No code fences. No markdown. Just the JSON object."""


def _build_user_prompt(
    top_push: list[str],
    top_interests: list[str],
    pace: str,
    constraints: TripConstraints,
    answers: PersonaQuestionAnswers,
) -> str:
    friends    = label_for("friends_would_say", constraints.friends_would_say) or "—"
    restaurant = label_for("restaurant_order",  constraints.restaurant_order)  or "—"
    notice     = label_for("what_you_notice",   constraints.what_you_notice)   or "—"
    atmosphere = label_for("ideal_atmosphere",  constraints.ideal_atmosphere)  or "—"
    small      = (answers.small_thing or "").strip() or "—"

    return f"""This user's persona signals:

Top motivations: {", ".join(top_push) or "—"}
Top interests: {", ".join(top_interests) or "—"}
Pace: {pace}

Their answers:
- Friends say they're the one who: {friends}
- At a new restaurant they: {restaurant}
- First thing they notice in a new place: {notice}
- Most at home in: {atmosphere}
- A small thing that made them happy lately: "{small}"

Write the JSON."""


# ── JSON parsing helpers ──────────────────────────────────────────────────────

def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    return m.group(1).strip() if m else raw


def _extract_json_object(raw: str) -> str:
    start = raw.find("{")
    if start == -1:
        raise ValueError("no JSON object found")
    depth, in_str, esc = 0, False, False
    for i in range(start, len(raw)):
        c = raw[i]
        if esc:
            esc = False
            continue
        if c == "\\" and in_str:
            esc = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return raw[start : i + 1]
    raise ValueError("unterminated JSON object")


def _parse_llm_json(raw: str) -> dict:
    obj = json.loads(_extract_json_object(_strip_fences(raw)))
    if not isinstance(obj, dict):
        raise ValueError("expected JSON object")
    desc = obj.get("descriptor", "")
    para = obj.get("paragraph", "")
    bulls = obj.get("bullets", [])
    if not (isinstance(desc, str) and isinstance(para, str) and isinstance(bulls, list)):
        raise ValueError("malformed shape")
    bulls = [b for b in bulls if isinstance(b, str) and b.strip()]
    if not desc.strip() or not para.strip() or not bulls:
        raise ValueError("empty fields")
    return {"descriptor": desc.strip(), "paragraph": para.strip(), "bullets": bulls}


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/persona-infer", response_model=PersonaInferResponse)
async def persona_infer(
    body: PersonaInferRequest,
    uid: str = Depends(verify_token),
) -> PersonaInferResponse:
    # Sanitize free-text before it hits the embedder or the LLM.
    answers = body.persona_answers.model_copy(update={
        "small_thing": sanitize_user_input(body.persona_answers.small_thing or ""),
    })
    constraints = body.constraints

    # 1. HF scoring (runs in a thread — sync HF encoder)
    persona = await asyncio.to_thread(infer_persona, constraints, answers)
    top_push, top_interests, pace = persona["top_push"], persona["top_interests"], persona["pace"]

    # 2. LLM-generated reveal copy via small-tier (persona_label).
    user_prompt = _build_user_prompt(top_push, top_interests, pace, constraints, answers)
    copy: dict | None = None
    try:
        raw = await route_request("persona_label", user_prompt, _SYSTEM_PROMPT)
        copy = _parse_llm_json(raw)
    except Exception as e:
        logger.warning("persona LLM failed (%s) — falling back to deterministic copy", e)

    # Fallback to deterministic tables if the LLM call or parse failed.
    if copy is None:
        bullet_keys = [
            constraints.friends_would_say,
            constraints.restaurant_order,
            constraints.what_you_notice,
            constraints.ideal_atmosphere,
        ]
        copy = {
            "descriptor": fallback_descriptor(top_push[0] if top_push else None,
                                              top_interests[0] if top_interests else None),
            "paragraph":  fallback_paragraph(top_push[0] if top_push else None),
            "bullets":    bullets_from_keys(bullet_keys)[:3],
        }

    return PersonaInferResponse(
        softener      = SOFTENER,
        descriptor    = copy["descriptor"],
        paragraph     = copy["paragraph"],
        bullets       = copy["bullets"],
        top_push      = top_push,
        top_interests = top_interests,
        pace          = pace,
        user_vector   = persona["user_vector"],
    )
