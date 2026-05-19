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

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
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

PUSH dimensions are MOTIVATIONS — why someone travels. Pick exactly 2 for top_push.
PULL dimensions are DESTINATION ATTRIBUTES — what they want at the place. Pick exactly 3 for top_interests.

These two pools are STRICTLY SEPARATE. Never put a PULL id into top_push, never put a PUSH id into top_interests. If unsure, re-read which pool a label belongs to before placing it.

PUSH ids (use ONLY these in top_push):

{push_vocab}

PULL ids (use ONLY these in top_interests):

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
- "bullets": exactly 3 phrases (5-12 words each), no period, lowercase start. Each phrase paraphrases ONE of the user's actual answers AND must be a NOUN PHRASE that completes the sentence "You're drawn to ___" grammatically. Do not start a bullet with a verb. Bad: "vanishes into new places and returns with stories" (verb phrase). Good: "the kind of night that ends with a story you didn't plan" (noun phrase). Bad: "drawn to neon and music" (starts with past participle). Good: "rooms where the bass hits you in the ribs" (noun phrase).

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


# ── Pool auto-correct ─────────────────────────────────────────────────────────

def _redistribute_pools(obj: dict) -> dict:
    """
    Move misplaced PUSH/PULL ids between top_push and top_interests. If the LLM
    put a valid PULL id into top_push (or vice versa), shift it to the right
    list rather than rejecting. Caps each list to the required size (2 push,
    3 pull) and deduplicates while preserving order.
    """
    if not isinstance(obj, dict):
        return obj
    raw_push = obj.get("top_push") if isinstance(obj.get("top_push"), list) else []
    raw_pull = obj.get("top_interests") if isinstance(obj.get("top_interests"), list) else []

    new_push: list[str] = []
    new_pull: list[str] = []
    for item in list(raw_push) + list(raw_pull):
        if not isinstance(item, str):
            continue
        if item in _ALLOWED_PUSH:
            new_push.append(item)
        elif item in _ALLOWED_PULL:
            new_pull.append(item)
        # Items in neither pool are dropped (LLM hallucinated).

    new_push = list(dict.fromkeys(new_push))[:2]
    new_pull = list(dict.fromkeys(new_pull))[:3]

    obj["top_push"] = new_push
    obj["top_interests"] = new_pull
    return obj


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

async def _bg_validate_persona(user_prompt: str, obj: dict) -> None:
    """
    Run the small-LLM semantic validator (NIM Nemotron Nano) after the response
    has been sent. Logs tone/echo/scope issues for observability without
    blocking the user flow. Never raises — failures fail open silently.
    """
    try:
        valid, issues = await validate_persona(user_prompt, obj)
        if not valid and issues:
            logger.warning("persona semantic validator flagged (non-blocking): %s", issues)
        else:
            logger.info("persona semantic validator passed")
    except Exception as e:
        logger.warning("persona semantic validator background task error: %s", e)


@router.post("/persona-infer", response_model=PersonaInferResponse)
async def persona_infer(
    body: PersonaInferRequest,
    background_tasks: BackgroundTasks,
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
    # The LLM keeps swapping a few PULL ids into top_push (process-verb keywords
    # in dims like exploration_local read as motivations to the model). Try to
    # auto-correct the pool placement first; only fall back to an LLM retry if
    # redistribution can't recover counts.
    issues = _structural_validate(obj)
    if issues:
        logger.warning("persona structural validation failed on first try: %s", issues)
        obj = _redistribute_pools(obj)
        issues = _structural_validate(obj)
        if not issues:
            logger.info("persona pools auto-corrected — no LLM retry needed")
        else:
            logger.warning("auto-correct insufficient (%s) — retrying with LLM correction", issues)
            correction = (
                f"\n\nYour previous JSON had these errors:\n- "
                + "\n- ".join(issues)
                + "\n\nReturn ONLY the corrected JSON object. Re-check that top_push uses ONLY PUSH ids and top_interests uses ONLY PULL ids."
            )
            try:
                raw_retry = await route_request("persona_label", user_prompt + correction, _system_prompt())
                obj = json.loads(_extract_json_object(_strip_fences(raw_retry)))
            except Exception as e:
                logger.error("persona retry failed: %s", e)
                raise HTTPException(status_code=502, detail=f"persona retry failed: {type(e).__name__}: {e}") from e
            obj = _redistribute_pools(obj)  # auto-correct retry output too
            issues = _structural_validate(obj)
            if issues:
                logger.error("persona structural validation failed after retry: %s", issues)
                raise HTTPException(status_code=502, detail=f"persona output invalid: {'; '.join(issues)}")

    # Fire-and-forget semantic validator. Runs the small-tier NIM critic after
    # FastAPI sends the response, so the user doesn't wait. Tone/echo issues
    # land in logs for observability; the user flow isn't gated on it.
    background_tasks.add_task(_bg_validate_persona, user_prompt, obj)

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
