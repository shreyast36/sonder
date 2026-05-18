"""
POST /api/persona-infer

Single-stage inference. HF and LLM run in parallel, then the small
cross-provider validator checks tone + echo + scope.

  ├─ HF embed persona text → durable user_vector
  ├─ Small LLM (Haiku via persona_label task) → top_push, top_interests,
  │                                              descriptor, paragraph, bullets
  └─ Small validator (Nemotron Nano) → schema + allowed-dim + quality checks

The LLM never sees Pinecone, never plans a trip. Itinerary generation only
fires after the user confirms the reveal on the frontend.
"""

import asyncio
import json
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from mushahid.auth import verify_token
from mushahid.utils.sanitize import sanitize_user_input
from mushahid.validation.critic import validate_persona
from shared.schemas import TripConstraints, PersonaQuestionAnswers
from jahnvi.data.dimensions import PUSH_DIMENSIONS, PULL_DIMENSIONS
from jahnvi.data.persona_labels import label_for
from jahnvi.data.convert_to_embeddings import embed_persona
from jahnvi.pipeline.module3_persona import _resolve_pace
from ali.routing.engine import route_request

router = APIRouter()
logger = logging.getLogger(__name__)

_SOFTENER = "Our read on you"
_ALLOWED_PUSH = list(PUSH_DIMENSIONS.keys())
_ALLOWED_PULL = list(PULL_DIMENSIONS.keys())


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

def _format_dimension_vocab(dims: dict[str, list[str]]) -> str:
    """Render dim IDs + their keyword lists as the LLM's ground-truth vocabulary."""
    lines = []
    for dim_id, keywords in dims.items():
        kw_str = ", ".join(keywords)
        lines.append(f"- {dim_id}: {kw_str}")
    return "\n".join(lines)


def _system_prompt() -> str:
    push_vocab = _format_dimension_vocab(PUSH_DIMENSIONS)
    pull_vocab = _format_dimension_vocab(PULL_DIMENSIONS)
    return f"""You read travel personas for an app's "here's who you are" reveal screen.

You are given the user's answers and must return BOTH the inferred dimension labels AND the reveal copy in one JSON object.

DIMENSION VOCABULARY — use these keyword lists as the source of truth for what each dimension means. Pick the dimension whose keywords best match the user's actual answers and free text. Never invent a label that isn't in this list.

PUSH dimensions (pick exactly 2 for top_push, ordered strongest first):

{push_vocab}

PULL dimensions (pick exactly 3 for top_interests, ordered strongest first):

{pull_vocab}

Voice rules for the reveal copy:
- Low-ego, concrete nouns, slightly self-aware. Not horoscope, not MBTI, not psychometric.
- Echo the user's actual answer choices — never invent specifics they didn't say.
- Editorial register — a travel magazine writer noticing something true about a person.

Return ONLY a JSON object with these keys:
- "top_push": list of 2 strings, each one of the allowed PUSH IDs above.
- "top_interests": list of 3 strings, each one of the allowed PULL IDs above.
- "descriptor": one short observational phrase, 4-9 words, no period.
- "paragraph": 2-3 sentences. How this person travels. Concrete. No archetype labels.
- "bullets": exactly 3 phrases (5-12 words each), no period, lowercase start. Each phrase paraphrases ONE of the user's actual answers.

No preamble. No code fences. No markdown. Just the JSON object."""


def _user_prompt(
    constraints: TripConstraints,
    answers: PersonaQuestionAnswers,
) -> str:
    friends    = label_for("friends_would_say", constraints.friends_would_say) or "—"
    restaurant = label_for("restaurant_order",  constraints.restaurant_order)  or "—"
    notice     = label_for("what_you_notice",   constraints.what_you_notice)   or "—"
    atmosphere = label_for("ideal_atmosphere",  constraints.ideal_atmosphere)  or "—"
    small      = (answers.small_thing or "").strip() or "—"
    pace       = _resolve_pace(constraints.pace)
    styles     = ", ".join(constraints.must_haves) if constraints.must_haves else "—"
    who        = constraints.who_travelling_with.value if constraints.who_travelling_with else "—"

    return f"""User's persona signals:

Travel style chips: {styles}
Pace: {pace}
Travelling with: {who}

Their persona answers:
- Friends say they're the one who: {friends}
- At a new restaurant they: {restaurant}
- First thing they notice in a new place: {notice}
- Most at home in: {atmosphere}
- A small thing that made them happy lately: "{small}"

Return the JSON."""


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
            esc = False; continue
        if c == "\\" and in_str:
            esc = True; continue
        if c == '"':
            in_str = not in_str; continue
        if in_str:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return raw[start : i + 1]
    raise ValueError("unterminated JSON object")


# ── Python structural validators ──────────────────────────────────────────────

def _structural_validate(obj: dict) -> list[str]:
    """Schema + allowed-dimension + count checks. Returns list of issues (empty = pass)."""
    issues: list[str] = []
    if not isinstance(obj, dict):
        return ["root is not an object"]

    tp = obj.get("top_push")
    if not isinstance(tp, list) or len(tp) != 2:
        issues.append("top_push must be a list of exactly 2 dimension IDs")
    elif any(p not in _ALLOWED_PUSH for p in tp):
        issues.append(f"top_push contains a dimension not in the allowed list: {tp}")

    ti = obj.get("top_interests")
    if not isinstance(ti, list) or len(ti) != 3:
        issues.append("top_interests must be a list of exactly 3 dimension IDs")
    elif any(p not in _ALLOWED_PULL for p in ti):
        issues.append(f"top_interests contains a dimension not in the allowed list: {ti}")

    desc = obj.get("descriptor", "")
    if not isinstance(desc, str) or not desc.strip():
        issues.append("descriptor is missing or empty")

    para = obj.get("paragraph", "")
    if not isinstance(para, str) or not para.strip():
        issues.append("paragraph is missing or empty")

    bullets = obj.get("bullets")
    if not isinstance(bullets, list) or len(bullets) != 3:
        issues.append("bullets must be a list of exactly 3 phrases")
    elif any(not isinstance(b, str) or not b.strip() for b in bullets):
        issues.append("bullets contains empty or non-string entries")

    # Guard against itinerary leakage.
    banned_keys = {"days", "activities", "itinerary", "destinations", "hotels"}
    if any(k in obj for k in banned_keys):
        issues.append(f"output contains itinerary keys: {sorted(set(obj.keys()) & banned_keys)}")

    return issues


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/persona-infer", response_model=PersonaInferResponse)
async def persona_infer(
    body: PersonaInferRequest,
    uid: str = Depends(verify_token),
) -> PersonaInferResponse:
    # Sanitize free-text before it hits the embedder or any LLM.
    answers = body.persona_answers.model_copy(update={
        "small_thing": sanitize_user_input(body.persona_answers.small_thing or ""),
    })
    constraints = body.constraints

    # Embedding and LLM persona call run in parallel — they don't depend on each other.
    user_prompt = _user_prompt(constraints, answers)
    embed_task = embed_persona(constraints, answers)
    llm_task   = route_request("persona_label", user_prompt, _system_prompt())

    try:
        user_vector, raw = await asyncio.gather(embed_task, llm_task)
    except Exception as e:
        logger.error("persona inference failed: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"persona inference failed: {type(e).__name__}: {e}") from e

    # Parse the LLM JSON.
    try:
        obj = json.loads(_extract_json_object(_strip_fences(raw)))
    except Exception as e:
        logger.error("persona LLM returned unparseable output: %s | raw=%r", e, raw[:500] if isinstance(raw, str) else raw)
        raise HTTPException(status_code=502, detail=f"persona LLM unparseable: {type(e).__name__}: {e}") from e

    # Structural validation — schema, allowed dimension IDs, counts, no itinerary leakage.
    issues = _structural_validate(obj)
    if issues:
        logger.error("persona structural validation failed: %s", issues)
        raise HTTPException(status_code=502, detail=f"persona output invalid: {'; '.join(issues)}")

    # Semantic validation — tone, echo, scope drift. Fails open on validator outage.
    valid, sem_issues = await validate_persona(user_prompt, obj)
    if not valid:
        logger.error("persona semantic validation failed: %s", sem_issues)
        raise HTTPException(status_code=502, detail=f"persona quality check failed: {'; '.join(sem_issues)}")

    return PersonaInferResponse(
        softener      = _SOFTENER,
        descriptor    = obj["descriptor"].strip(),
        paragraph     = obj["paragraph"].strip(),
        bullets       = [b.strip() for b in obj["bullets"]],
        top_push      = obj["top_push"],
        top_interests = obj["top_interests"],
        pace          = _resolve_pace(constraints.pace),
        user_vector   = user_vector,
    )
