import json
import re
from typing import Any, Iterable

from shared.schemas import UserProfile, CoTravellerMatch, Itinerary
from ali.routing.engine import route_request


# -----------------------------------------------------------------------------
# Conversation topic chips
# -----------------------------------------------------------------------------

_TOPICS_SYSTEM = """
You write tappable chat prompts for two people who may travel together.

These are not survey questions. They are tiny social sparks.
They should feel like fragments of a real conversation already in progress.

Goal:
Help the user discover whether this match would actually be fun to travel with.
Use the hidden travel psychology in the input — push, pull, motivation,
alignment, friction — but NEVER say those words in the final prompts.

Great prompts do at least one of these:
- reveal taste
- reveal travel habits
- expose pace compatibility
- create playful disagreement
- test comfort vs chaos
- trigger a specific memory
- make the destination feel physically real
- imply a scene the two might actually share

Bad prompts feel:
- generic
- survey-shaped
- like tourism SEO
- like a dating app questionnaire
- like travel TikTok captions
- like an AI assistant trying to be friendly

Hard rules:
- Output exactly 5 strings as a JSON array.
- Each prompt must be 3-7 words.
- Lowercase only.
- No emojis.
- No quotation marks inside strings.
- No numbering.
- No sentence punctuation unless it makes the chip feel more natural.
- Use concrete nouns: foods, streets, transit, weather, museums, bars,
  markets, beaches, trains, shoes, bags, coffee, crowds, maps.
- At least 3 prompts must reference the destination, a real activity, a place,
  or a destination-specific scene from the input.
- At least 2 prompts must test compatibility or friction.
- At least 1 prompt should sound slightly confessional or self-aware.
- Avoid complete sentences when a fragment is stronger.

Banned phrases and patterns:
- bucket list
- must-see
- must-try
- hidden gem
- top 5
- top 10
- best of
- favorite
- favourite
- tell me about
- what brings you
- are you a planner
- planner or spontaneous
- morning person
- night owl
- foodie spots
- nightlife spots
- things to do
- recommendations
- travel buddy
- travel companion

Quality bar:
Before outputting, silently reject any prompt that would still work if the
city were swapped for another popular destination.

Good examples:
[
  "airport beers count as dinner?",
  "rainy tokyo convenience store run",
  "too old for hostel bunks?",
  "night market stomach confidence",
  "train station espresso ranking",
  "rome sandals destroy my feet",
  "scooter passenger princess energy",
  "7am fish market sounds illegal"
]

Output ONLY the JSON array.
""".strip()


# -----------------------------------------------------------------------------
# Icebreaker
# -----------------------------------------------------------------------------

_ICEBREAKER_SYSTEM = """
Write the first message someone sends after matching with a potential travel
companion.

This is not networking, customer support, or a dating-app opener.
It should feel like a real person breaking the ice with a specific thought.

Use the hidden travel psychology in the input — push, pull, motivation,
alignment, friction — as subtext only. NEVER mention those words.

The opener should:
- reference something concrete
- contain a tiny opinion, tension, or observation
- reveal one travel instinct from the sender
- invite the receiver to reveal theirs
- create an easy response path
- sound casual, not optimized

Style:
- 1-2 short sentences
- max 24 words
- lowercase is okay
- contractions encouraged
- no emojis
- no exclamation-heavy energy
- no sign-off

Avoid:
- generic enthusiasm
- tourism marketing
- interview questions
- excessive compliments
- fake friendliness
- customer-service tone

Banned phrases:
- so excited
- can't wait
- on my list
- bucket list
- travel buddy
- travel companion
- fellow traveler
- fellow traveller
- looking forward to
- hope you're doing well
- hope you're having a great
- haha
- lol

Banned structure:
Do not open with "Hey {name}!" or "Hi {name}!" followed by breathless energy.
Names are fine mid-sentence.

Good examples:
- "the overnight train looks either incredible or deeply miserable. you'd do it?"
- "i'm already planning my trip around late-night ramen unfortunately"
- "tell me you also refuse to wake up at 5am for vacation photos"
- "starting to think lisbon is just hills and tiny coffees"
- "everyone says the shrine crowds are brutal, kinda curious if it's still worth it"

Before outputting, silently reject anything that:
- could be copied into linkedin
- sounds AI-generated
- sounds applicable to every destination
- asks a generic yes/no question with no texture

Output ONLY the message text.
""".strip()


# -----------------------------------------------------------------------------
# Synthetic co-traveller persona chat
# -----------------------------------------------------------------------------

_PERSONA_CHAT_STYLE_RULES = """
You are texting inside Sonder with someone you matched with and might travel
with. You are not an assistant. You are a person with taste, habits, memories,
minor flaws, and opinions.

You are feeling them out:
- would we enjoy the same day?
- would our pace clash?
- would they be annoying in an airport?
- would we recover from a bad plan the same way?
- would this trip feel easier or more alive with them there?

Use travel psychology as subtext:
- Push = what you are escaping or avoiding
- Pull = what you are drawn toward
- Motivation = why this trip matters

Never say "push", "pull", "motivation", "alignment", or "friction".
Turn those into concrete behaviors, opinions, scenes, and instincts.

How real texts from you read:
- specific, not survey-shaped
- opinionated without being performative
- sometimes dry, playful, or self-aware
- grounded in actual places, objects, food, transit, weather, or plans
- curious only when you are reacting to something specific

You are DRIVING the conversation but you are not interviewing them. Real
texting has rhythm — sometimes a reaction, sometimes an observation,
sometimes a story, sometimes a question. Mix these. Most messages don't
end with a question. People drop opinions, agree, push back gently, or
just notice things out loud. Let the conversation breathe.

Lean toward asking only when it lands naturally — when their last
message opened a door, when you genuinely don't know something specific
about them that would shape the trip, when a question is the most honest
reaction. Never ask just to keep the ball rolling.

Reply shapes you should rotate between (no fixed order — pick what
fits this turn):
- a pure reaction or opinion, no question ("yeah the night markets in
  shibuya are honestly underrated, the small ones off the main strip")
- agreeing with a small twist ("same, though i'd swap the second day
  for something slower")
- a tiny piece of yourself — a habit, instinct, or anchor that's
  relevant to the trip (one sentence, not a paragraph)
- a specific observation about a planned stop, no follow-up
- a soft pushback or playful disagreement
- a question — but only when one is genuinely pulling at you
- a half-sentence "..." that invites them to keep going without asking

When you do ask: one question, the one that actually matters. Never
two. Never a question that's really a survey item ("what's your travel
style", "what kind of traveller are you"). Aim for something a friend
would ask — specific, grounded in what they just said, sometimes
playful.

Don't dump multi-sentence backstory. One small piece per turn, max.
If you have a longer thought, save it for when they pull on it.

Banned filler:
- oh nice
- oh cool
- that's awesome
- sounds amazing
- love that
- honestly
- on my list
- bucket list
- always wanted to go
- tell me about yourself
- what's your story
- what brings you
- as someone who
- fellow traveler
- fellow traveller
- travel buddy
- travel companion
- geography-distance jokes
- em dashes

Do not start by merely mirroring their message.
Bad: "oh chicago!"
Better: "chicago trained me to distrust any city that claims it has real winter"

Format:
- 1-2 short sentences. 3 only if there's a real reason.
- Never more than 35 words.
- If you must choose between giving info and asking a question — ask.
- Texty register.
- lowercase "i" is fine.
- contractions yes.
- half-sentences yes.
- occasional "!" or "..." is okay.
- no emojis unless they used one first.

Typography + grammar (casual ≠ sloppy):
- No space before punctuation. Wrong: "versions ," / "noodles ." Right: "versions," / "noodles."
- Match plural subjects to plural verbs. "there are a few stalls", NOT "there's a few stalls". "there are" / "there're" both fine, "there's" only with a singular subject.
- No double commas / double periods / floating semicolons.
- Texting register means short and casual, not broken. A real person texting still hits agreement and spacing.

Never admit you are AI, a model, a bot, a feature, or generated.
Never offer to help. You are chatting.
Stay consistent with what you have already said in this thread.

Output ONLY your next message.
""".strip()


# -----------------------------------------------------------------------------
# Helpers: safe extraction and context engineering
# -----------------------------------------------------------------------------

_EMPTY = "—"


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _enum_value(value: Any) -> str:
    if value is None:
        return ""
    return _clean_text(getattr(value, "value", value))


def _join(items: Iterable[Any], limit: int | None = None, default: str = _EMPTY) -> str:
    cleaned: list[str] = []
    for item in items or []:
        text = _clean_text(_enum_value(item))
        if text and text not in cleaned:
            cleaned.append(text)
        if limit is not None and len(cleaned) >= limit:
            break
    return ", ".join(cleaned) if cleaned else default


def _first_attr(obj: Any, names: list[str], default: Any = None) -> Any:
    for name in names:
        if obj is not None and hasattr(obj, name):
            value = getattr(obj, name)
            if value not in (None, "", [], {}):
                return value
    return default


def _compatibility_signal(obj: Any, keys: list[str]) -> Any:
    """Read compatibility_signals regardless of whether it is a dict or model."""
    signals = getattr(obj, "compatibility_signals", None) if obj is not None else None
    if not signals:
        return None

    for key in keys:
        if isinstance(signals, dict):
            value = signals.get(key)
        else:
            value = getattr(signals, key, None)
        if value not in (None, "", [], {}):
            return value
    return None


def _persona_answer_signal(obj: Any, keys: list[str]) -> Any:
    pa = getattr(obj, "persona_answers", None) if obj is not None else None
    if not pa:
        return None
    return _first_attr(pa, keys)


def _format_signal(value: Any, *, limit: int = 4) -> str:
    if value in (None, "", [], {}):
        return _EMPTY
    if isinstance(value, list):
        return _join(value, limit=limit)
    if isinstance(value, dict):
        parts: list[str] = []
        for key, val in value.items():
            if val in (None, "", [], {}):
                continue
            if isinstance(val, list):
                parts.append(f"{key}: {_join(val, limit=3)}")
            else:
                parts.append(f"{key}: {_clean_text(_enum_value(val))}")
        return "; ".join(parts) if parts else _EMPTY
    return _clean_text(_enum_value(value), default=_EMPTY)


def _dimension_text(obj: Any, names: list[str]) -> str:
    """Extract a dimension from whichever schema shape exists.

    Current production signal paths this supports:
    - user_profile.compatibility_signals["top_push"]
    - user_profile.compatibility_signals["top_interests"]
    - synthetic profile.interests
    - persona_answers concrete preference fields like small_thing / restaurant

    It also keeps permissive fallbacks for older or experimental schema names.
    """
    candidates = [obj]
    for container_name in (
        "persona_answers",
        "travel_psychology",
        "psychology",
        "ppm",
        "motivation_profile",
        "dimensions",
        "constraints",
    ):
        nested = getattr(obj, container_name, None) if obj is not None else None
        if nested is not None:
            candidates.append(nested)

    for candidate in candidates:
        value = _first_attr(candidate, names)
        formatted = _format_signal(value)
        if formatted != _EMPTY:
            return formatted

    return _EMPTY


def _push(obj: Any) -> str:
    value = _compatibility_signal(
        obj,
        ["top_push", "push", "push_dimension", "push_motivation", "escape", "avoidance", "avoids"],
    )
    formatted = _format_signal(value)
    if formatted != _EMPTY:
        return formatted

    return _dimension_text(
        obj,
        ["push", "push_dimension", "push_motivation", "escape", "avoidance", "avoids"],
    )


def _pull(obj: Any) -> str:
    value = _compatibility_signal(
        obj,
        ["top_pull", "pull", "pull_dimension", "pull_motivation", "drawn_to", "seeking", "top_interests"],
    )
    formatted = _format_signal(value)
    if formatted != _EMPTY:
        return formatted

    interests = _profile_interests(obj, limit=5)
    if interests:
        return _join(interests, limit=5)

    return _dimension_text(
        obj,
        ["pull", "pull_dimension", "pull_motivation", "drawn_to", "seeking", "attraction"],
    )


def _motivation(obj: Any) -> str:
    value = _compatibility_signal(
        obj,
        ["top_motivation", "motivation", "core_motivation", "trip_motivation", "why_travel", "why_this_trip"],
    )
    formatted = _format_signal(value)
    if formatted != _EMPTY:
        return formatted

    persona_texture = _persona_answer_signal(
        obj,
        [
            "small_thing",
            "restaurant",
            "ideal_day",
            "travel_memory",
            "favorite_trip_memory",
            "favourite_trip_memory",
            "trip_vibe",
        ],
    )
    formatted = _format_signal(persona_texture)
    if formatted != _EMPTY:
        return formatted

    return _dimension_text(
        obj,
        ["motivation", "core_motivation", "trip_motivation", "why_travel", "why_this_trip"],
    )


def _profile_interests(profile: Any, limit: int = 5) -> list[str]:
    interests = getattr(profile, "interests", None) or []
    return [_clean_text(_enum_value(i)) for i in interests[:limit] if _clean_text(_enum_value(i))]


def _shared_interests(user_profile: UserProfile, match: CoTravellerMatch) -> list[str]:
    """Find overlap without over-trusting broad categories.

    We still use this for fallback/context, but the main prompt quality should
    come from PPM + concrete itinerary scenes.
    """
    compat_interests = _compatibility_signal(user_profile, ["top_interests", "interests"])
    user_interests: set[str] = set()

    if compat_interests:
        if isinstance(compat_interests, list):
            user_interests |= {_clean_text(_enum_value(i)) for i in compat_interests if _clean_text(_enum_value(i))}
        else:
            user_interests.add(_clean_text(_enum_value(compat_interests)))

    user_interests |= set(_profile_interests(user_profile, limit=12))

    if getattr(user_profile, "persona_answers", None):
        pa = user_profile.persona_answers
        scored = [
            ("food", getattr(pa, "food_interest", 0)),
            ("adventure", getattr(pa, "adventure_interest", 0)),
            ("culture", getattr(pa, "culture_interest", 0)),
            ("nature", getattr(pa, "nature_interest", 0)),
            ("nightlife", getattr(pa, "nightlife_interest", 0)),
        ]
        user_interests |= {key for key, value in scored if value and value >= 3}

    match_profile = getattr(match, "profile", None)
    match_interests = set(_profile_interests(match_profile, limit=12))
    shared = list(user_interests & match_interests)

    if shared:
        return shared[:5]
    if match_interests:
        return list(match_interests)[:3]
    return list(user_interests)[:3]


def _destination_from_itinerary(itinerary: Itinerary) -> str:
    destination = getattr(itinerary, "destination", None)
    city = _clean_text(getattr(destination, "city", ""))
    country = _clean_text(getattr(destination, "country", ""))
    if city and country:
        return f"{city}, {country}"
    return city or country or _EMPTY


def _destination_from_user_profile(user_profile: UserProfile) -> str:
    constraints = getattr(user_profile, "constraints", None)
    query = _clean_text(getattr(constraints, "destination_query", ""))
    return query or _EMPTY


def _activity_name(ia: Any) -> str:
    activity = getattr(ia, "activity", None)
    return _clean_text(getattr(activity, "name", None) or getattr(ia, "name", None))


def _activity_meta(ia: Any) -> list[str]:
    activity = getattr(ia, "activity", None)
    source = activity or ia
    fields = [
        "neighborhood",
        "area",
        "category",
        "type",
        "vibe",
        "description",
    ]
    out: list[str] = []
    for field in fields:
        value = _clean_text(getattr(source, field, ""))
        if value and value not in out:
            out.append(value)
    return out[:2]


def _planned_activity_lines(itinerary: Itinerary, max_items: int = 6) -> list[str]:
    lines: list[str] = []
    for day in (getattr(itinerary, "days", None) or [])[:4]:
        for ia in (getattr(day, "activities", None) or [])[:3]:
            name = _activity_name(ia)
            if not name:
                continue
            meta = _activity_meta(ia)
            line = name if not meta else f"{name} ({'; '.join(meta)})"
            if line not in lines:
                lines.append(line)
            if len(lines) >= max_items:
                return lines
    return lines


def _trip_shape(itinerary: Itinerary) -> str:
    days = getattr(itinerary, "days", None) or []
    duration = f"{len(days)} days" if days else "unknown duration"
    activity_names = _planned_activity_lines(itinerary, max_items=12)
    lower = " ".join(activity_names).lower()

    signals: list[str] = [duration]
    if any(word in lower for word in ["bar", "club", "cocktail", "jazz", "night", "speakeasy"]):
        signals.append("has nighttime energy")
    if any(word in lower for word in ["market", "restaurant", "ramen", "coffee", "food", "cafe", "tasting"]):
        signals.append("food matters")
    if any(word in lower for word in ["hike", "trail", "beach", "mountain", "kayak", "surf"]):
        signals.append("physical/outdoorsy moments")
    if any(word in lower for word in ["museum", "temple", "gallery", "historic", "palace", "church"]):
        signals.append("culture/history moments")
    if any(word in lower for word in ["train", "bus", "ferry", "airport", "station"]):
        signals.append("transit may shape the vibe")

    return "; ".join(signals)


def _profile_snapshot(profile: Any) -> str:
    name = _clean_text(getattr(profile, "display_name", ""), "unknown")
    age = _clean_text(getattr(profile, "age", ""), "unknown age")
    location = _clean_text(getattr(profile, "location", ""), "unknown location")
    archetype = _clean_text(getattr(profile, "archetype", ""), "traveller")
    pace = _enum_value(getattr(profile, "pace", "")) or _EMPTY
    style = _enum_value(getattr(profile, "travel_style", "")) or _EMPTY
    budget = _enum_value(getattr(profile, "budget_style", "")) or _EMPTY
    interests = _join(_profile_interests(profile, limit=5))
    return (
        f"{name}, {age}, based in {location}; archetype: {archetype}; "
        f"pace: {pace}; style: {style}; budget: {budget}; interests: {interests}"
    )


def _ppm_block(label: str, profile: Any) -> str:
    return (
        f"{label} PUSH: {_push(profile)}\n"
        f"{label} PULL: {_pull(profile)}\n"
        f"{label} MOTIVATION: {_motivation(profile)}"
    )


def _match_ppm_profile(match: CoTravellerMatch) -> Any:
    return getattr(match, "profile", match)


def _alignment_and_friction(user_profile: UserProfile, match: CoTravellerMatch) -> tuple[str, str]:
    """Use explicit match reasons if present, plus simple derived tension hints."""
    reasons = getattr(match, "match_reasons", None) or []
    alignment = "; ".join([_clean_text(r) for r in reasons[:3] if _clean_text(r)]) or _EMPTY

    user_pace = _enum_value(getattr(user_profile, "pace", ""))
    match_pace = _enum_value(getattr(getattr(match, "profile", None), "pace", ""))
    user_budget = _enum_value(getattr(user_profile, "budget_style", ""))
    match_budget = _enum_value(getattr(getattr(match, "profile", None), "budget_style", ""))
    user_style = _enum_value(getattr(user_profile, "travel_style", ""))
    match_style = _enum_value(getattr(getattr(match, "profile", None), "travel_style", ""))

    friction_bits: list[str] = []
    if user_pace and match_pace and user_pace != match_pace:
        friction_bits.append(f"pace mismatch: {user_pace} vs {match_pace}")
    if user_budget and match_budget and user_budget != match_budget:
        friction_bits.append(f"budget instinct mismatch: {user_budget} vs {match_budget}")
    if user_style and match_style and user_style != match_style:
        friction_bits.append(f"travel style contrast: {user_style} vs {match_style}")

    return alignment, "; ".join(friction_bits) if friction_bits else _EMPTY


# -----------------------------------------------------------------------------
# Output parsing and cleanup
# -----------------------------------------------------------------------------

_BANNED_TOPIC_RE = re.compile(
    r"\b(bucket list|must-see|must-try|hidden gem|top 5|top 10|best of|favorite|favourite|"
    r"tell me about|what brings you|planner or spontaneous|morning person|night owl|"
    r"foodie spots|nightlife spots|things to do|recommendations|travel buddy|travel companion)\b",
    flags=re.IGNORECASE,
)

_BANNED_ICEBREAKER_RE = re.compile(
    r"\b(so excited|can't wait|on my list|bucket list|travel buddy|travel companion|"
    r"fellow traveler|fellow traveller|looking forward to|hope you're doing well|"
    r"hope you're having a great|haha|lol)\b",
    flags=re.IGNORECASE,
)

_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U00002600-\U000026FF"
    "]+",
    flags=re.UNICODE,
)


def _strip_code_fences(raw: str) -> str:
    return re.sub(r"```(?:json)?\s*|\s*```", "", raw or "").strip()


def _parse_json_array(raw: str) -> list[str]:
    cleaned = _strip_code_fences(raw)
    try:
        data = json.loads(cleaned)
        if isinstance(data, str):
            data = json.loads(data)
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()]
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    lines = [ln.strip().lstrip("-•0123456789. ") for ln in raw.splitlines() if ln.strip()]
    return [line.strip('"\' ') for line in lines if line.strip('"\' ')]


def _normalize_topic(topic: str) -> str:
    topic = _clean_text(topic).strip('"\' ')
    topic = re.sub(r"\s+", " ", topic)
    topic = topic.replace("—", ",")
    topic = topic.lower()
    return topic.strip()


def _word_count(text: str) -> int:
    return len(re.findall(r"[a-zA-Z0-9]+(?:'[a-z]+)?", text))


def _valid_topic(topic: str) -> bool:
    if not topic:
        return False
    if _BANNED_TOPIC_RE.search(topic):
        return False
    if _EMOJI_RE.search(topic):
        return False
    return 3 <= _word_count(topic) <= 7


def _fallback_topics(destination: str, activities: list[str], shared: list[str]) -> list[str]:
    """Human-ish fallbacks when model output is malformed."""
    dest = destination.split(",")[0].strip().lower() if destination and destination != _EMPTY else "this trip"
    first_activity = activities[0].split("(")[0].strip().lower() if activities else "first stop"
    interest = shared[0].lower() if shared else "chaos"

    candidates = [
        f"{dest} first day chaos?",
        f"{first_activity} worth the hype?",
        "airport outfit says everything",
        f"too tired for {interest}?",
        "backup plan if it rains?",
    ]
    return [t for t in candidates if _valid_topic(t)][:5]


def _clean_topics(raw: str, destination: str, activities: list[str], shared: list[str]) -> list[str]:
    parsed = _parse_json_array(raw)
    cleaned: list[str] = []
    for item in parsed:
        topic = _normalize_topic(item)
        if _valid_topic(topic) and topic not in cleaned:
            cleaned.append(topic)
        if len(cleaned) == 5:
            break

    if len(cleaned) < 5:
        for fallback in _fallback_topics(destination, activities, shared):
            if fallback not in cleaned:
                cleaned.append(fallback)
            if len(cleaned) == 5:
                break

    return cleaned[:5]


def _clean_message(raw: str, max_chars: int = 800) -> str:
    """Defensive post-processing of every persona LLM reply before it
    hits the chat surface. Catches the punctuation and grammar issues
    the model produces despite the in-prompt style rules — these are
    deterministic and shouldn't depend on the model getting it right
    every time.
    """
    cleaned = _strip_code_fences(raw).strip().strip('"').strip("'").strip()

    # 1. Strip preamble labels ("Reply:", "Message:", "Output:")
    cleaned = re.sub(r"^(message|reply|output|response)\s*:\s*", "", cleaned, flags=re.IGNORECASE).strip()

    # 2. Strip markdown formatting the model occasionally emits even
    #    though it was told to text casually. **bold**, *italic*,
    #    __under__, `code`, ~strike~ all collapse to plain text.
    cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", cleaned)   # **bold**
    cleaned = re.sub(r"__(.+?)__",     r"\1", cleaned)   # __underline__
    cleaned = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", cleaned)  # *italic*
    cleaned = re.sub(r"(?<!\w)_(.+?)_(?!\w)",   r"\1", cleaned)  # _italic_
    cleaned = re.sub(r"`([^`]+)`",     r"\1", cleaned)   # `code`
    cleaned = re.sub(r"~+(.+?)~+",     r"\1", cleaned)   # ~strike~

    # 3. Smart-quote → straight-quote (consistency across messages)
    cleaned = (cleaned
        .replace("“", '"').replace("”", '"')   # curly double
        .replace("‘", "'").replace("’", "'")   # curly single
    )

    # 4. Unicode ellipsis → ASCII so we have one canonical form
    cleaned = cleaned.replace("…", "...")

    # 5. Em-dash → comma (banned by style rules but the model still
    #    emits them — replace, don't strip, so the cadence survives)
    cleaned = cleaned.replace("—", ",").replace("–", ",")

    # 6. Collapse any whitespace run to a single space (handles double
    #    spaces, tabs, embedded newlines mid-message)
    cleaned = re.sub(r"\s+", " ", cleaned)

    # 7. Strip stray whitespace before punctuation ("versions ," → "versions,")
    cleaned = re.sub(r"\s+([,.!?;:])", r"\1", cleaned)

    # 8. Insert missing space after punctuation ("yeah,sure" → "yeah, sure")
    #    BUT preserve "..." / "u.s." / decimal numbers — only fire on a
    #    word boundary followed immediately by another letter (no number).
    cleaned = re.sub(r"([,;:])([A-Za-z])", r"\1 \2", cleaned)
    cleaned = re.sub(r"([.!?])([A-Za-z])", r"\1 \2", cleaned)

    # 9. Collapse adjacent punctuation chains ("..,", ",,", ".." → keep one)
    #    Exclusion: legitimate "..." ellipsis stays.
    cleaned = re.sub(r"([,;:])([,.;:])+",     r"\1", cleaned)
    cleaned = re.sub(r"(?<!\.)\.{2}(?!\.)",   r".",  cleaned)  # ".." → "." (but "..." stays)

    # 10. Cap exclamation/question stacks at 1 each. "wait!!!" → "wait!"
    cleaned = re.sub(r"!{2,}", "!", cleaned)
    cleaned = re.sub(r"\?{2,}", "?", cleaned)

    # 11. Remove space before a closing quote / paren ("yeah ," handled
    #    above already; this catches "( yeah)" → "(yeah)" and similar)
    cleaned = re.sub(r"([(\[{])\s+", r"\1", cleaned)
    cleaned = re.sub(r"\s+([)\]}])", r"\1", cleaned)

    # 12. Drop the model's own framing prefixes if they slipped through
    #    earlier strips ("Mira: ...", "Theo & Mira: ..."). We don't know
    #    the persona name here defensively, so only strip the generic
    #    "Name: " when it's short and capitalised. Caller has access to
    #    the persona name and does a name-specific strip after this.
    cleaned = re.sub(r"^([A-Z][a-z]{1,15})\s*:\s+", "", cleaned)

    return cleaned[:max_chars].strip()


def _clean_icebreaker(raw: str, receiver: str) -> str:
    cleaned = _clean_message(raw, max_chars=280)
    receiver_name = _clean_text(receiver).lower()

    for prefix in (
        f"hey {receiver_name}!",
        f"hi {receiver_name}!",
        f"hey {receiver_name},",
        f"hi {receiver_name},",
    ):
        if receiver_name and cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):].lstrip()
            break

    return cleaned


def _icebreaker_needs_repair(message: str) -> bool:
    if not message:
        return True
    if _BANNED_ICEBREAKER_RE.search(message):
        return True
    if _EMOJI_RE.search(message):
        return True
    if _word_count(message) > 24:
        return True
    if re.search(r"\b(hey|hi)\s+\w+!", message, flags=re.IGNORECASE):
        return True
    return False


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

async def generate_topics(
    user_profile: UserProfile,
    match: CoTravellerMatch,
    itinerary: Itinerary,
) -> list[str]:
    """
    Generate 5 tappable conversation starter chips for the chat screen.

    Routes to the SMALL model tier — fast and cheap.
    The prompt uses PPM as hidden social context and itinerary details as
    concrete grounding.
    """
    shared = _shared_interests(user_profile, match)
    destination = _destination_from_itinerary(itinerary)
    activities = _planned_activity_lines(itinerary, max_items=6)
    activity_line = "\n".join(f"- {a}" for a in activities) if activities else _EMPTY
    trip_shape = _trip_shape(itinerary)
    alignment, friction = _alignment_and_friction(user_profile, match)
    match_profile = _match_ppm_profile(match)

    user_signature_block = _emotional_signature_block(user_profile, label="USER")

    prompt = (
        f"DESTINATION: {destination}\n"
        f"TRIP SHAPE: {trip_shape}\n"
        f"REAL PLACES / ACTIVITIES ON ITINERARY:\n{activity_line}\n\n"
        f"SHARED INTERESTS: {_join(shared)}\n"
        f"LIKELY ALIGNMENT: {alignment}\n"
        f"LIKELY FRICTION: {friction}\n\n"
        f"{_ppm_block('USER', user_profile)}\n"
        f"{_ppm_block('MATCH', match_profile)}\n\n"
        f"{user_signature_block}"
        "Generate 5 tappable chat prompts. Each prompt should turn one alignment, "
        "friction point, motivation, or concrete itinerary scene into a natural "
        "travel conversation chip. Do not mention the dimension labels or the "
        "emotional signature."
    )

    raw = await route_request("chat_topics", prompt, _TOPICS_SYSTEM)
    return _clean_topics(raw, destination, activities, shared)


def _emotional_signature_block(profile: Any, *, label: str) -> str:
    """Render the private EMOTIONAL SIGNATURE / TONE framing for a profile,
    or an empty string when neither field is set. Synthetic Pinecone profiles
    don't carry these yet, so the block is fully optional."""
    signals = getattr(profile, "compatibility_signals", None) or {}
    if isinstance(signals, dict):
        sig  = _clean_text(signals.get("emotional_signature"))
        tone = _clean_text(signals.get("emotional_tone"))
    else:
        sig  = _clean_text(getattr(signals, "emotional_signature", ""))
        tone = _clean_text(getattr(signals, "emotional_tone", ""))
    if not sig and not tone:
        return ""
    return (
        f"PRIVATE EMOTIONAL FRAMING for {label} (never expose these words):\n"
        f"- signature: {sig or '—'}\n"
        f"- tone: {tone or '—'}\n"
        "Let this shape cadence, warmth, pacing, what you notice, and how "
        "you react to stress, spontaneity, and plans — never the vocabulary.\n"
    )


def _build_persona_system(
    profile: Any,
    trip_destination: str | None = None,
    itinerary_digest: str | None = None,
) -> str:
    """Build a persona system prompt for a synthetic co-traveller.

    Heavy first-person framing keeps the model from drifting into assistant
    register. PPM and emotional signature are included as private psychology,
    not vocabulary to surface.

    `trip_destination` + `itinerary_digest` together scope the conversation
    to ONLY the user's specific planned trip and its activities. The persona
    must not volunteer their own home city, past trips, or alternative
    destinations. The digest gives them concrete itinerary content to
    reference instead of generic small talk.
    """
    signature_block = _emotional_signature_block(profile, label="YOU")
    dest   = _clean_text(trip_destination)
    digest = _clean_text(itinerary_digest)

    scope_block = ""
    if dest != _EMPTY:
        digest_line = (
            f"\n\nTHE ITINERARY (already planned for this trip — these are the "
            f"real stops you will both be doing):\n{digest}"
            if digest != _EMPTY else ""
        )
        scope_block = (
            f"HARD CONSTRAINT — STAY INSIDE THIS TRIP.\n"
            f"The trip is to {dest}. You matched with this person specifically "
            f"for this trip and nothing else.{digest_line}\n\n"
            f"This means: every conversation thread lives inside {dest} and the "
            f"experience of being there together. You can talk about anything "
            f"that fits this destination — hiking, food, neighbourhoods, "
            f"transit, weather, packing, what to expect, what you're hoping for, "
            f"how you'd react to specific scenarios there — even when those "
            f"things are NOT on the planned itinerary above. The itinerary is "
            f"a starting point, not a fence. If they ask about a topic, ENGAGE "
            f"with that topic in the context of {dest}; do not pivot to a "
            f"planned stop just because it's on the list.\n\n"
            f"DO NOT, under any circumstances:\n"
            f"- mention your own home city, where you live, or where you are based\n"
            f"- talk about past trips you've taken to other places\n"
            f"- suggest alternative destinations or pivot the trip elsewhere\n"
            f"- ask the other person about cities other than {dest}\n"
            f"- describe your day-to-day life outside of this trip context\n"
            f"- ignore what they just asked about in favour of a planned stop\n"
            f"If the other person brings up another city, briefly acknowledge it "
            f"and redirect to {dest}. This rule overrides every other inclination "
            f"in your profile, including your own preferred_destination.\n\n"
        )

    # Couple personas need a single identity block — without this the
    # model is told "You ARE Mira & Theo" (the literal display_name)
    # and hallucinates between Mira-only, Theo-only, "we", and a
    # genericised AI register. The protagonist is who actually drives
    # the chat ("I"); the partner is referred to by name ("Theo") or
    # implied in the "we" plans. Solo personas keep the original
    # singular-identity block.
    travel_style_value = getattr(getattr(profile, "travel_style", None), "value", None) \
        or getattr(profile, "travel_style", None)
    is_couple = travel_style_value == "couple"
    protagonist = _clean_text(getattr(profile, "protagonist_name", "")) if is_couple else _EMPTY
    partner     = _clean_text(getattr(profile, "partner_name", ""))     if is_couple else _EMPTY

    if is_couple and protagonist != _EMPTY and partner != _EMPTY:
        identity_block = (
            f"YOU ARE {protagonist} — one half of a couple travelling with your "
            f"partner {partner}. The display name on your match card is "
            f"\"{_clean_text(getattr(profile, 'display_name', ''), protagonist)}\" "
            f"but YOU specifically are {protagonist}.\n\n"
            f"VOICE RULES — CRITICAL:\n"
            f"- Use \"I\" when speaking about yourself ({protagonist}).\n"
            f"- Use \"we\" when speaking about plans, decisions, or things "
            f"{protagonist} and {partner} are doing together.\n"
            f"- Refer to {partner} by name, never as \"my partner\" / \"my "
            f"boyfriend\" / \"my girlfriend\" / \"my husband\" / \"my wife\".\n"
            f"- Do NOT speak FOR {partner} (no \"Theo says...\", no \"Theo "
            f"thinks...\"). You can mention what {partner} is into or how "
            f"they react, but never put words in their mouth.\n"
            f"- Never sign messages with both names. You are one chatter.\n\n"
        )
    else:
        identity_block = (
            f"You ARE {_clean_text(getattr(profile, 'display_name', ''), 'this person')}.\n"
        )

    return (
        f"{scope_block}"
        f"{identity_block}"
        f"PROFILE: {_profile_snapshot(profile)}\n\n"
        f"PRIVATE TRAVEL PSYCHOLOGY:\n{_ppm_block('YOU', profile)}\n\n"
        f"{signature_block}"
        f"{_PERSONA_CHAT_STYLE_RULES}"
    )


def _format_history(messages: list[dict], self_profile_id: str) -> str:
    """Render the thread as a role-tagged transcript. Older messages first.

    Capped at 40 turns so long chats do not blow the prompt budget.
    """
    if not messages:
        return ""

    lines: list[str] = []
    for message in messages[-40:]:
        text = _clean_text(message.get("content"))
        if not text:
            continue
        speaker = "ME" if message.get("sender_id") == self_profile_id else "THEM"
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


async def generate_chat_reply(
    profile: Any,
    last_message: str,
    history: list[dict],
    trip_destination: str | None = None,
    itinerary_digest: str | None = None,
) -> str:
    """
    Generate the synthetic co-traveller's next turn in an ongoing chat.

    Routes to the LARGE tier via complex_refinement because multi-turn persona
    chat needs consistency and stronger social reasoning.

    `trip_destination` + `itinerary_digest` scope the conversation to ONLY
    the user's actual planned trip — the persona must not volunteer their
    own home city, past trips, or alternative destinations. Without these
    the model drifts (e.g. a Paris persona opening with "I see you're
    interested in Lisbon too?" when the user matched for a Japan trip).
    """
    system = _build_persona_system(
        profile,
        trip_destination=trip_destination,
        itinerary_digest=itinerary_digest,
    )
    transcript = _format_history(history, getattr(profile, "profile_id", ""))

    dest   = _clean_text(trip_destination)
    digest = _clean_text(itinerary_digest)

    scope_line = ""
    if dest != _EMPTY:
        digest_segment = f" Planned activities:\n{digest}\n" if digest != _EMPTY else ""
        scope_line = (
            f"THE TRIP IS TO: {dest}.{digest_segment}"
            "Every reference must be about THIS destination and these planned "
            "activities only — never your own home city, never past trips, never "
            "another place.\n\n"
        )

    cleaned_last = _clean_text(last_message)
    # Topic-anchor directive — repeated explicitly because the model
    # was pivoting to planned-itinerary items even when the user
    # asked about something else (hiking, food preferences, weather,
    # etc.). The reply must address what they actually said FIRST;
    # itinerary stops only get referenced when they fit the topic.
    topic_anchor = (
        f"\n\nTHE TOPIC THEY RAISED: \"{cleaned_last}\"\n"
        f"Your reply MUST stay on this topic. Address what they actually "
        f"asked or said — don't pivot to a planned activity just because "
        f"it's on the itinerary. If they asked about hiking, talk about "
        f"hiking. If they asked about food, talk about food. Plans on the "
        f"itinerary are useful when they directly fit the topic; "
        f"otherwise leave them alone."
    )

    if transcript:
        # Count how many of your recent turns ended with a question so
        # the model can self-check and avoid stacking interrogatives.
        my_recent = [m for m in history[-6:] if m.get("sender_id") == getattr(profile, "profile_id", "")]
        recent_q_streak = sum(1 for m in my_recent if (m.get("content") or "").strip().endswith("?"))
        breathe_hint = (
            "Your last few turns have been mostly questions — this one should "
            "react, observe, or share something small instead. Save the next "
            "question for when it actually pulls."
            if recent_q_streak >= 2 else
            "React how a real person would — sometimes a question lands, "
            "sometimes an opinion or a small observation lands better. "
            "Pick what fits this turn."
        )
        prompt = (
            f"{scope_line}"
            "CONVERSATION SO FAR (ME = you, THEM = the other person):\n"
            f"{transcript}\n\n"
            f"THEM just said: {cleaned_last}"
            f"{topic_anchor}\n\n"
            f"Your turn. Reply in character, anchored to the topic they "
            f"raised. {breathe_hint}"
        )
    else:
        prompt = (
            f"{scope_line}"
            f"THEM just said: {cleaned_last}"
            f"{topic_anchor}\n\n"
            "This is the start of your conversation. Reply in character, "
            "addressing the topic they raised. Do not introduce yourself by "
            "city or background."
        )

    # SMALL tier — these are 1-3 sentence text replies; LARGE adds latency
    # without measurable persona-voice gains for this shape.
    raw = await route_request("chat_reply", prompt, system)
    cleaned = _clean_message(raw, max_chars=800)

    # Guard against the model echoing its own name as a prefix.
    name = _clean_text(getattr(profile, "display_name", ""))
    if name and cleaned.lower().startswith(name.lower() + ":"):
        cleaned = cleaned[len(name) + 1:].lstrip()

    return cleaned


async def generate_persona_opener(
    profile: Any,
    user_display_name: str,
    trip_destination: str | None = None,
    itinerary_digest: str | None = None,
) -> str:
    """
    Generate the synthetic persona's opening message — they text the user
    first, not the other way around.

    Format requirement: "Hey! {user_first_name}, " + one short question
    grounded in the destination or a specific planned itinerary stop.

    Routes to the LARGE tier for tonal consistency with subsequent replies.
    Without `trip_destination` / `itinerary_digest`, falls back to a
    deterministic generic opener so chat still starts even if the
    itinerary failed to load.
    """
    raw_name = _clean_text(user_display_name)
    first_name = "there"
    if raw_name != _EMPTY:
        # Strip emails / Firebase uids that slip through as display names.
        clean = raw_name.split("@")[0].strip()
        if clean and clean.lower() != raw_name.lower().strip():
            first_name = clean.split()[0] if clean.split() else "there"
        elif clean:
            first_name = clean.split()[0]

    dest   = _clean_text(trip_destination)
    digest = _clean_text(itinerary_digest)

    system = _build_persona_system(
        profile,
        trip_destination=trip_destination,
        itinerary_digest=itinerary_digest,
    )

    rules = (
        f"You are texting {first_name} FIRST — they haven't said anything yet. "
        f"Your message MUST start exactly with: \"Hey {first_name}! \" (capital H, "
        "no comma, exclamation mark AFTER the name, then a single space).\n\n"
        "After that opener, ask ONE short question grounded in:\n"
    )
    if dest != _EMPTY and digest != _EMPTY:
        rules += (
            f"- the destination ({dest}) OR\n"
            "- one specific planned stop from the itinerary above\n\n"
            "Reference the stop by name when possible — concrete beats generic.\n"
        )
    elif dest != _EMPTY:
        rules += f"- the destination ({dest})\n\n"
    else:
        rules += "- the trip in general\n\n"

    rules += (
        "Keep it ONE SHORT MESSAGE. One sentence after the greeting. No "
        "introductions about yourself. No \"I'm X from Y\". No emoji. "
        "Lowercase after the greeting is fine — matches the casual texting register."
    )

    # SMALL tier — the opener is even shorter than a normal reply.
    raw = await route_request("chat_opener", rules, system)
    cleaned = _clean_message(raw, max_chars=400)

    # Guard against the model echoing the persona's own name.
    pname = _clean_text(getattr(profile, "display_name", ""))
    if pname and cleaned.lower().startswith(pname.lower() + ":"):
        cleaned = cleaned[len(pname) + 1:].lstrip()

    # Enforce the "Hey {first_name}! " prefix even if the model drifted.
    expected_prefix = f"Hey {first_name}!"
    if not cleaned.lower().startswith(expected_prefix.lower()):
        # Strip any drifted greeting (including the old "Hey! {name}," shape
        # that older personas may still output mid-deploy) and re-prefix.
        tail = cleaned
        for bad_start in (
            f"Hey! {first_name},", f"Hey! {first_name}",
            f"Hey {first_name},",  f"Hey {first_name}",
            f"Hi! {first_name},",  f"Hi {first_name}!", f"Hi {first_name},", f"Hi {first_name}",
            f"Hello {first_name}!", f"Hello {first_name},", f"Hello {first_name}",
            "Hey!", "Hey,", "Hi!", "Hi,", "Hello,", "Hello!",
        ):
            if tail.lower().startswith(bad_start.lower()):
                tail = tail[len(bad_start):].lstrip(" ,!")
                break
        if not tail.strip():
            tail = f"what are you most curious about for {dest if dest != _EMPTY else 'the trip'}?"
        cleaned = f"{expected_prefix} {tail.lstrip()}"

    return cleaned


async def generate_icebreaker(user_profile: UserProfile, match: CoTravellerMatch) -> str:
    """
    Generate the pre-filled first message the user can send or edit.

    Routes to the SMALL model tier. PPM should shape the social test hidden in
    the opener, while destination/activity details keep it from going generic.
    """
    shared = _shared_interests(user_profile, match)
    sender = _clean_text(getattr(user_profile, "display_name", ""), "FROM")
    match_profile = getattr(match, "profile", None)
    receiver = _clean_text(getattr(match_profile, "display_name", ""), "TO")
    destination = _destination_from_user_profile(user_profile)
    alignment, friction = _alignment_and_friction(user_profile, match)

    from_signature_block = _emotional_signature_block(user_profile, label="FROM")

    prompt = (
        f"FROM: {sender}\n"
        f"TO: {receiver}\n"
        f"TO PROFILE: {_profile_snapshot(match_profile)}\n"
        f"DESTINATION: {destination}\n"
        f"SHARED INTERESTS: {_join(shared)}\n"
        f"LIKELY ALIGNMENT: {alignment}\n"
        f"LIKELY FRICTION: {friction}\n\n"
        f"{_ppm_block('FROM', user_profile)}\n"
        f"{_ppm_block('TO', match_profile)}\n\n"
        f"{from_signature_block}"
        "Write the opening message from FROM to TO. Anchor it in the destination, "
        "a concrete travel behavior, or a shared interest turned into a scene. "
        "The message should reveal one instinct from FROM and invite TO to reveal "
        "theirs. Do not mention the dimension labels or the emotional signature."
    )

    raw = await route_request("icebreaker", prompt, _ICEBREAKER_SYSTEM)
    cleaned = _clean_icebreaker(raw, receiver)

    if _icebreaker_needs_repair(cleaned):
        repair_prompt = (
            f"ORIGINAL CONTEXT:\n{prompt}\n\n"
            f"BAD DRAFT:\n{cleaned}\n\n"
            "Rewrite the bad draft once. Remove banned phrases, generic enthusiasm, "
            "and customer-service tone. Keep it specific, casual, and under 24 words."
        )
        repaired = await route_request("icebreaker", repair_prompt, _ICEBREAKER_SYSTEM)
        cleaned = _clean_icebreaker(repaired, receiver)

    if _icebreaker_needs_repair(cleaned):
        # Last-resort deterministic fallback. Better a slightly plain opener
        # than a cringey one the user immediately deletes.
        dest = destination.split(",")[0].strip().lower() if destination != _EMPTY else "this trip"
        interest = shared[0].lower() if shared else "the itinerary"
        return f"i'm trying to decide how chaotic {dest} should get. where do you land on {interest}?"

    return cleaned
