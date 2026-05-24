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

import sentry_sdk
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from mushahid.auth import verify_token
from mushahid.utils.sanitize import sanitize_user_input
from mushahid.validation.critic import validate_persona
from shared.schemas import TripConstraints, PersonaQuestionAnswers
from jahnvi.data.dimensions import (
    PUSH_DIMENSIONS, PULL_DIMENSIONS,
    MIN_TOP_PUSH, MAX_TOP_PUSH, MIN_TOP_PULL, MAX_TOP_PULL,
)
from jahnvi.data.persona_labels import label_for
from jahnvi.data.convert_to_embeddings import embed_persona
from jahnvi.data.classify_emotions import classify_emotions
from jahnvi.pipeline.module3_persona import _resolve_pace
from ali.routing.engine import route_request, route_request_structured

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
    # Emotional signature — private framing only. The raw key is never shown
    # to the user (downstream consumers use it to shape tone), but the human-
    # readable emotional_tone phrase can be surfaced as flavor copy.
    emotional_tone: str | None = None


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

PUSH dimensions are MOTIVATIONS — why someone travels. Pick {MIN_TOP_PUSH} to {MAX_TOP_PUSH} for top_push — all the ones that genuinely apply to this user, no more, no fewer. Most users have 2-3 strong push motivations; pick more when their answers clearly span more, pick fewer when only one shows through. Do not pad to a fixed count.
PULL dimensions are DESTINATION ATTRIBUTES — what they want at the place. Pick {MIN_TOP_PULL} to {MAX_TOP_PULL} for top_interests — same rule, all the ones that genuinely apply. Multiple pull interests are common.

These two pools are STRICTLY SEPARATE. Never put a PULL id into top_push, never put a PUSH id into top_interests. If unsure, re-read which pool a label belongs to before placing it.

How to read the radio answers (use these as your strongest signals, not your only ones):
- "The best trips leave them feeling…" is the CLEANEST push signal — "brain got louder" → stimulation/curiosity, "disappeared from normal life" → escape/reset, "collected stories" → narrative/social, "exhaled properly" → recovery/reset. Anchor at least one top_push here.
- "On a trip people rely on them for…" reveals social role + emotional regulation under chaos. Use it to disambiguate between similar PUSH dimensions and to inform the descriptor.
- "When something goes wrong mid-day they…" reveals resilience and control orientation — not a dimension label itself, but a strong texture signal for the paragraph + bullets. Surface it as concrete behaviour.
- "They instantly feel at home in places that are…" is the strongest stimulation-threshold + atmosphere signal — maps directly to PULL ids about scene/energy.
- The free-text small thing is gold for metaphor and aesthetic register. Echo a fragment of it into one bullet when possible.

PUSH ids (use ONLY these in top_push):

{push_vocab}

PULL ids (use ONLY these in top_interests):

{pull_vocab}

Voice rules for the reveal copy:
- Low-ego, concrete nouns, slightly self-aware. Not horoscope, not MBTI, not psychometric.
- Echo the user's actual answer choices — never invent specifics they didn't say.
- Editorial register — a travel magazine writer noticing something true about a person.

BANNED — if any of these appear, the output is wrong:
- "soul", "spirit", "essence", "energy" (and any "X-soul/-spirit" compound)
- "wanderer", "explorer at heart", "free spirit", "old soul"
- "always craving", "forever chasing", "the kind of person who…" (especially in the descriptor — too horoscope)
- "in your element", "lights you up", "speaks to you", "calls to you"
- "embraces", "thrives", "savours" (LLM travel-writing tells)
- "off-the-beaten-path", "hidden gem", "tucked away" (lazy travel clichés)
- "you're drawn to…" inside the paragraph — the word "drawn" already prefixes the bullets, so don't repeat it in the prose.
- Exclamation marks. Em-dashes. Quotes around the user's selections in the paragraph (paraphrase, don't quote).

Return ONLY a JSON object with these keys:
- "top_push": list of {MIN_TOP_PUSH}-{MAX_TOP_PUSH} strings, each one of the allowed PUSH IDs above. Self-defined count — pick all that genuinely apply, don't pad.
- "top_interests": list of {MIN_TOP_PULL}-{MAX_TOP_PULL} strings, each one of the allowed PULL IDs above. Self-defined count.
- "descriptor": one short observational phrase, 4-9 words, no period.
- "paragraph": 2-3 sentences. How this person travels. Concrete. No archetype labels.
- "bullets": exactly 3 phrases (5-12 words each), no period, lowercase start. Each phrase paraphrases ONE of the user's actual answers AND must be a NOUN PHRASE that completes the sentence "You're drawn to ___" grammatically. Do not start a bullet with a verb. Bad: "vanishes into new places and returns with stories" (verb phrase). Good: "the kind of night that ends with a story you didn't plan" (noun phrase). Bad: "drawn to neon and music" (starts with past participle). Good: "rooms where the bass hits you in the ribs" (noun phrase).

No preamble. No code fences. No markdown. Just the JSON object."""


def _group_framing(constraints: TripConstraints) -> str:
    """Per-group-type guidance for the persona LLM.

    The same persona answers read differently depending on who's on the
    trip. A solo traveller's social_role answer reveals their isolated
    instincts; a couple's reveals the dynamic between two people; a
    family lead's reveals the role they take inside a group; a friend-
    group lead's reveals the social register they bring to a peer
    setting. The reveal copy must use the right grammatical lens (you /
    you both / your family / your group) and read the same persona
    primitives through that lens — not the same paragraph with pronouns
    swapped.

    This block is appended to the system prompt; downstream the
    paragraph + bullets + descriptor all need to honour it."""
    style = constraints.who_travelling_with
    n = max(1, int(constraints.group_size or 1))
    if style is None:
        return ""
    if style.value == "solo":
        return (
            "TRIP SHAPE: solo traveller (party of 1).\n"
            "Read the persona answers as their isolated instincts. Use "
            "second-person singular ('you', 'your'). The reveal is about "
            "how this one person travels — pace they set when nobody else "
            "is anchoring them, how they handle their own friction, what "
            "they gravitate toward when nobody else is voting."
        )
    if style.value == "couple":
        return (
            "TRIP SHAPE: a couple travelling together (party of 2).\n"
            "Read the persona answers as the DYNAMIC between them, not "
            "just one half. The 'they' / 'them' in the answers refers to "
            "the user; the reveal should land on the trip THEY shape "
            "together. Use second-person 'you' (the user) but lean into "
            "phrases that imply the partner is present — 'the kind of "
            "evening you'd both linger in', 'rooms you'd choose together'. "
            "Don't invent the partner's traits; do let the trip feel "
            "shared rather than solo."
        )
    if style.value == "family":
        return (
            f"TRIP SHAPE: family trip of {n}.\n"
            "Read the persona answers as the role this person takes inside "
            "the group. social_role + friction_response reveal how they "
            "ABSORB or REGULATE the family's energy under stress; "
            "ideal_atmosphere reveals what atmosphere they'd lobby the "
            "family toward. The reveal should describe the trip 'your "
            "family' would take with this person setting the tone. Use "
            "'you' and 'your family' — not 'they'. Lean into anchors that "
            "imply mixed ages and shared meals; avoid late-night / "
            "high-stimulation framing unless the answers explicitly point "
            "there."
        )
    if style.value == "friends":
        return (
            f"TRIP SHAPE: trip with friends, group of {n}.\n"
            "Read the persona answers as the social register this person "
            "brings to a peer group. social_role reveals what slot they "
            "play in the group (planner / regulator / hype / connector); "
            "trip_feeling reveals what THEY want the group to come away "
            "with, even if others want different things. The reveal "
            "describes the trip 'you and your group' would take with this "
            "person setting the tone. Use 'you' and 'your group' / 'the "
            "group' — not 'they'. Lean into anchors that imply shared "
            "decisions and overlapping energy levels."
        )
    return ""


def _user_prompt(
    constraints: TripConstraints,
    answers: PersonaQuestionAnswers,
) -> str:
    social     = label_for("social_role",       constraints.social_role)       or "—"
    feeling    = label_for("trip_feeling",      constraints.trip_feeling)      or "—"
    friction   = label_for("friction_response", constraints.friction_response) or "—"
    atmosphere = label_for("ideal_atmosphere",  constraints.ideal_atmosphere)  or "—"
    small      = (answers.small_thing or "").strip() or "—"
    pace       = _resolve_pace(constraints.pace)
    styles     = ", ".join(constraints.must_haves) if constraints.must_haves else "—"
    who        = constraints.who_travelling_with.value if constraints.who_travelling_with else "—"
    party      = max(1, int(constraints.group_size or 1))
    group_block = _group_framing(constraints)

    framing_section = f"{group_block}\n\n" if group_block else ""

    return f"""{framing_section}User's persona signals:

Travel style chips: {styles}
Pace: {pace}
Travelling with: {who} (party of {party})

Their persona answers:
- On a trip people rely on them for: {social}
- The best trips leave them feeling: {feeling}
- When something goes wrong mid-day they: {friction}
- They instantly feel at home in places that are: {atmosphere}
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
    list rather than rejecting. Caps each list to 6 (the full vocabulary size)
    and deduplicates while preserving order. Counts are self-defined per
    persona — 1-6 each — so we no longer pad short lists; only the truly
    empty-after-redistribute case gets a single fallback id (otherwise the
    structural validator's min-1 rule would 502).
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

    new_push = list(dict.fromkeys(new_push))[:MAX_TOP_PUSH]
    new_pull = list(dict.fromkeys(new_pull))[:MAX_TOP_PULL]

    # Only fall back when the redistribute produced an empty list AND the
    # validator's minimum requires at least 1. If MIN_TOP_PUSH is set to 0
    # (empty allowed) this branch is a no-op.
    if MIN_TOP_PUSH > 0 and not new_push and _ALLOWED_PUSH:
        new_push = [_ALLOWED_PUSH[0]]
    if MIN_TOP_PULL > 0 and not new_pull and _ALLOWED_PULL:
        new_pull = [_ALLOWED_PULL[0]]

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
    if not isinstance(tp, list) or not (MIN_TOP_PUSH <= len(tp) <= MAX_TOP_PUSH):
        issues.append(f"top_push must be a list of {MIN_TOP_PUSH} to {MAX_TOP_PUSH} dimension IDs")
    elif any(p not in _ALLOWED_PUSH for p in tp):
        issues.append(f"top_push contains a dimension not in the allowed list: {tp}")

    ti = obj.get("top_interests")
    if not isinstance(ti, list) or not (MIN_TOP_PULL <= len(ti) <= MAX_TOP_PULL):
        issues.append(f"top_interests must be a list of {MIN_TOP_PULL} to {MAX_TOP_PULL} dimension IDs")
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

async def _bg_validate_persona(user_prompt: str, obj: dict, uid: str = "") -> None:
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
        try:
            from mushahid.monitoring import capture, EVENT_PERSONA_VALIDATION
            capture(uid or "anonymous", EVENT_PERSONA_VALIDATION, {
                "valid":        valid,
                "issue_count":  len(issues),
                "issues":       issues[:5],  # sample only — UI dashboards don't need full list
            })
        except Exception:
            pass
    except Exception as e:
        logger.warning("persona semantic validator background task error: %s", e)


@router.post("/persona-infer", response_model=PersonaInferResponse)
async def persona_infer(
    body: PersonaInferRequest,
    background_tasks: BackgroundTasks,
    uid: str = Depends(verify_token),
) -> PersonaInferResponse:
    sentry_sdk.set_user({"id": uid})
    # Sanitize free-text before it hits the embedder or any LLM.
    answers = body.persona_answers.model_copy(update={
        "small_thing": sanitize_user_input(body.persona_answers.small_thing or ""),
    })
    constraints = body.constraints

    # Embedding + emotion classification run in parallel; the LLM call then
    # uses the classifier output to ground its persona tone (reduces tonal
    # hallucination from the LLM since it has explicit emotional anchors
    # detected from the user's actual free text).
    user_prompt_base = _user_prompt(constraints, answers)
    embed_task    = embed_persona(constraints, answers)
    classify_task = classify_emotions(
        # Free text is the strongest signal of tone; fall back to the
        # picker labels concatenated when small_thing is empty.
        (answers.small_thing or "").strip() or
        " ".join(filter(None, [
            label_for("social_role",       constraints.social_role),
            label_for("trip_feeling",      constraints.trip_feeling),
            label_for("friction_response", constraints.friction_response),
            label_for("ideal_atmosphere",  constraints.ideal_atmosphere),
        ])),
        top_k=5,
    )

    try:
        user_vector, emotion_signals = await asyncio.gather(embed_task, classify_task)
    except Exception as e:
        logger.error("persona pre-LLM step failed: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"persona pre-LLM step failed: {type(e).__name__}: {e}") from e

    # Build the grounded user prompt. Top emotions get injected as a
    # short anchor so the LLM doesn't invent tones the text doesn't carry.
    emotion_grounding = ""
    if emotion_signals:
        top_labels = ", ".join(label for label, _ in emotion_signals[:5])
        emotion_grounding = (
            f"\n\nEMOTIONAL REGISTER (top GoEmotions labels by cosine similarity "
            f"against the user's free text): {top_labels}.\n"
            "Keep the descriptor / paragraph / bullets consistent with these "
            "emotions. Do not introduce tones the user's text does not carry."
        )
    user_prompt = user_prompt_base + emotion_grounding

    # Run the main persona LLM and the emotional-signature classifier in
    # parallel. Both consume the same goemotions output, so the signature
    # inferrer reuses ours via precomputed_goemotions to avoid a second
    # text-embed call.
    from mushahid.persona.emotional_signature import infer_emotional_signature
    from mushahid.persona.taxonomy import (
        EMOTIONAL_SIGNATURE_TAXONOMY, PERSONA_QUESTION_CATALOG,
    )
    signature_inputs = {
        "social_role":       constraints.social_role,
        "trip_feeling":      constraints.trip_feeling,
        "friction_response": constraints.friction_response,
        "ideal_atmosphere":  constraints.ideal_atmosphere,
        "small_thing":       (answers.small_thing or "").strip(),
    }
    main_persona_task = route_request_structured(
        "persona_label", user_prompt, _system_prompt(),
        push_ids=_ALLOWED_PUSH, pull_ids=_ALLOWED_PULL,
    )
    signature_task = infer_emotional_signature(
        signature_inputs,
        question_catalog=PERSONA_QUESTION_CATALOG,
        signature_taxonomy=EMOTIONAL_SIGNATURE_TAXONOMY,
        precomputed_goemotions=emotion_signals,
    )
    try:
        raw, signature_result = await asyncio.gather(main_persona_task, signature_task)
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
                raw_retry = await route_request_structured(
                    "persona_label", user_prompt + correction, _system_prompt(),
                    push_ids=_ALLOWED_PUSH, pull_ids=_ALLOWED_PULL,
                )
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
    background_tasks.add_task(_bg_validate_persona, user_prompt, obj, uid)

    # Persist the inferred persona + this trip's constraints back to the user
    # profile so downstream matching (/api/cotraveller) has real signals to
    # score against instead of falling back to the neutral 0.5 baseline
    # (which made every match score the same ~28%).
    try:
        from mushahid.realtime.firestore import update_user_profile
        from shreyas.ranking.salience import compute_answer_salience
        compat_signals: dict = {
            "top_push":       obj["top_push"],
            "top_interests":  obj["top_interests"],
            "pace":           _resolve_pace(constraints.pace),
            "top_emotions":   [label for label, _ in emotion_signals],
            "emotion_scores": {label: round(score, 4) for label, score in emotion_signals},
        }
        # Layer the emotional signature on top — chat reply, why_this,
        # icebreaker, topics, and the persona card all read these keys as
        # private framing (the raw signature key is never user-facing).
        compat_signals.update(signature_result.to_compatibility_signals())
        # Per-question salience for the ranking engine — read by the
        # salience_weighted_question_overlap feature at match time. Pure
        # function, no LLM call, no extra latency.
        compat_signals["answer_salience"] = compute_answer_salience(answers, constraints)

        # Analytics: persona inference complete. Powers cohort analysis
        # ("what % of users land as story_collector vs quiet_observer?") +
        # salience entropy lets us spot users who left most answers blank.
        try:
            import math
            from mushahid.monitoring import capture, EVENT_PERSONA_INFERRED
            sal = compat_signals.get("answer_salience") or {}
            entropy = -sum(p * math.log(p) for p in sal.values() if p > 0)
            capture(uid, EVENT_PERSONA_INFERRED, {
                "emotional_signature":            signature_result.emotional_signature,
                "emotional_tone":                 signature_result.emotional_tone,
                "emotional_signature_confidence": signature_result.confidence,
                "top_push":                       obj["top_push"],
                "top_interests":                  obj["top_interests"],
                "salience_entropy":               round(entropy, 3),
                "small_thing_length":             len((answers.small_thing or "").strip()),
            })
        except Exception:
            pass

        await update_user_profile(uid, {
            "compatibility_signals": compat_signals,
            "travel_style_embedding": user_vector,
            "constraints":            constraints.model_dump(mode="json"),
            "persona_answers":        answers.model_dump(mode="json"),
        })
    except Exception as e:
        logger.warning("persist persona to user_profile failed: %s", e)

    return PersonaInferResponse(
        softener       = _SOFTENER,
        descriptor     = obj["descriptor"].strip(),
        paragraph      = obj["paragraph"].strip(),
        bullets        = [b.strip() for b in obj["bullets"]],
        top_push       = obj["top_push"],
        top_interests  = obj["top_interests"],
        pace           = _resolve_pace(constraints.pace),
        user_vector    = user_vector,
        emotional_tone = signature_result.emotional_tone,
    )
