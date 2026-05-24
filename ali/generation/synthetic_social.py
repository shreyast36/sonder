"""
Persona-voiced content for the synthetic-agents background loop.

Two helpers:
    generate_synthetic_post(persona)            → str  (a social post)
    generate_synthetic_open_trip_note(persona,  → str  (a one-line "open
                                     city, country)       to companions"
                                                          note for /discover)

Both are SMALL tier — short, conversational, no JSON. Failures bubble
up to the caller (the agent loop), which logs and drops the cycle so a
single LLM hiccup doesn't kill the loop.
"""

from __future__ import annotations

import logging
from typing import Any

from ali.routing.engine import route_request

logger = logging.getLogger(__name__)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _persona_block(persona: Any) -> str:
    def g(attr: str) -> str:
        return _clean(getattr(persona, attr, ""))
    parts: list[str] = []
    name = g("display_name")
    if name:
        parts.append(f"Name: {name}")
    archetype = g("archetype")
    if archetype:
        parts.append(f"Archetype: {archetype}")
    location = g("location")
    if location:
        parts.append(f"Based in: {location}")
    pace = g("pace")
    if pace:
        parts.append(f"Pace: {pace}")
    budget = g("budget_style")
    if budget:
        parts.append(f"Budget: {budget}")
    style = g("travel_style")
    if style:
        parts.append(f"Style: {style}")
    interests = getattr(persona, "interests", None) or []
    if interests:
        parts.append(f"Interests: {', '.join(str(i) for i in interests[:6])}")
    quirks = getattr(persona, "quirks", None) or []
    if quirks:
        parts.append(f"Quirks: {', '.join(str(q) for q in quirks[:3])}")
    return "\n".join(parts) if parts else "(no profile fields available)"


_POST_SYSTEM_PROMPT = """\
You are roleplaying as a real person about to write ONE short social
post on a travel app's feed.

Voice:
- texting register, casual, slightly off-the-cuff
- 1-3 sentences, never more than 4
- contractions, mild uncertainty, understated tone
- can mention a specific city, food, mood, plan, regret, recommendation
- no hashtags, no emoji, no "AI", no "as a traveller", no app jargon

Forbidden:
- "I can help" / "Here are" / "Based on" / "My recommendation"
- "travel buddy" / "wanderlust" / "bucket list" / "hidden gem"
- multi-paragraph essays
- bullet lists
- assistant phrasing

Pick exactly ONE of these post shapes to write:
- a tiny memory ("the coffee outside that one bakery in lisbon still
  ruins every other coffee for me")
- a half-formed plan ("thinking of going somewhere quiet next month,
  maybe the slovenian alps, idk")
- a small recommendation ("if anyone's in oaxaca: the mezcal place on
  Garcia Vigil with the green door, that's it")
- a candid observation ("airports at 5am hit different, half the
  people look like they regret everything")
- a soft question ("anyone been to taipei in march? wondering if the
  rain is as constant as people say")

Return ONLY the post text. No prefix, no quotes, no commentary."""


async def generate_synthetic_post(persona: Any) -> str:
    """One short post in the persona's voice. Returns "" on failure
    so the caller can skip cleanly."""
    prompt = (
        "PERSONA:\n"
        f"{_persona_block(persona)}\n\n"
        "Write one post they'd plausibly write right now."
    )
    try:
        raw = await route_request("chat_reply", prompt, _POST_SYSTEM_PROMPT)
    except Exception as e:
        logger.warning("generate_synthetic_post: route_request failed: %s", e)
        return ""
    text = (raw or "").strip()
    if text.startswith('"') and text.endswith('"') and len(text) > 1:
        text = text[1:-1].strip()
    return text[:600]


_OPEN_TRIP_SYSTEM_PROMPT = """\
You are roleplaying as a real person opening up their upcoming trip to
co-travellers on a travel app.

Write ONE short note (1-2 sentences) that would appear next to the
trip card on a discovery feed. It should:
- sound human, like texting, slightly tentative
- hint at what kind of company they'd want without listing criteria
- avoid sales language, hashtags, emoji, and app jargon

Bad:
- "Join me for an unforgettable adventure!"
- "Looking for like-minded travel buddies."
- "Open to wanderlust-loving souls."

Good:
- "low-key trip, mostly walking and eating. would be nice not to do it alone."
- "going for a wedding then staying a few extra days, open to whoever's around."
- "thinking slow mornings, late dinners, one museum if we feel like it."

Return ONLY the note text. No prefix, no quotes."""


_OUTREACH_SYSTEM_PROMPT = """\
You are roleplaying as a real person on a travel app who just noticed
another user's upcoming trip and wants to start a chat — because the
trip overlaps with something you care about (you've been there, you
were thinking of going, you have a tip, you're curious about a
specific part of it).

Write the FIRST message of that chat. The other person hasn't said
anything yet. You're the one breaking the ice.

Voice:
- texting register, casual, slightly tentative ("hey, saw your kyoto
  trip — were you thinking of doing nara as a day trip too?")
- 1-2 short sentences, never more than 3
- ONE specific reference to their trip (city, dates, or a planned
  stop) — not generic "your trip looks fun"
- end with EITHER a soft question OR a half-thought that invites a
  reply — never a hard sell
- contractions, lowercase 'i' is fine, no emoji unless the trip cues
  one naturally
- NEVER mention algorithms, matching, the app, "compatibility",
  scores, or that you noticed their profile

Forbidden openers:
- "hi! i couldn't help but notice..."
- "your trip sounds amazing!!"
- "wanderlust" / "bucket list" / "travel buddy"
- "i think we'd be a great match for"
- "i love that you're going to"

Good shapes:
- "hey, saw you're going to lisbon in march — i was there in feb,
  the rain was lighter than i expected. you doing any day trips?"
- "noticed kyoto on your trip card. random question: are you planning
  to do the philosopher's path? was deciding whether to add it for
  mine."
- "oaxaca in october — are you going for the day of the dead, or
  trying to avoid it?"

Return ONLY the message text. No quotes, no preamble, no commentary."""


async def generate_outreach_opener(
    persona: Any,
    target_destination_city: str,
    target_destination_country: str = "",
    target_trip_window: str = "",
) -> str:
    """First message in a cold-outreach chat the persona is starting
    with a real user. Anchored in ONE specific thing about the user's
    trip so it reads as 'I noticed a particular thing', not 'I noticed
    you exist'."""
    where = target_destination_city
    if target_destination_country:
        where = f"{target_destination_city}, {target_destination_country}"
    when_line = f" (dates: {target_trip_window})" if target_trip_window else ""
    prompt = (
        "PERSONA:\n"
        f"{_persona_block(persona)}\n\n"
        f"THE OTHER PERSON'S TRIP: {where}{when_line}.\n\n"
        "Write the first message you'd send them. Pick ONE specific "
        "anchor about the trip to reference; don't be generic."
    )
    try:
        raw = await route_request("chat_reply", prompt, _OUTREACH_SYSTEM_PROMPT)
    except Exception as e:
        logger.warning("generate_outreach_opener: route_request failed: %s", e)
        return ""
    text = (raw or "").strip()
    if text.startswith('"') and text.endswith('"') and len(text) > 1:
        text = text[1:-1].strip()
    return text[:400]


async def generate_synthetic_open_trip_note(
    persona: Any, city: str, country: str,
) -> str:
    """A one-line note the persona attaches to their open trip card."""
    where = city
    if country:
        where = f"{city}, {country}"
    prompt = (
        "PERSONA:\n"
        f"{_persona_block(persona)}\n\n"
        f"They're opening a trip to {where} for companions. "
        "Write the note that goes on the trip card."
    )
    try:
        raw = await route_request("chat_reply", prompt, _OPEN_TRIP_SYSTEM_PROMPT)
    except Exception as e:
        logger.warning("generate_synthetic_open_trip_note: route_request failed: %s", e)
        return ""
    text = (raw or "").strip()
    if text.startswith('"') and text.endswith('"') and len(text) > 1:
        text = text[1:-1].strip()
    return text[:200]
