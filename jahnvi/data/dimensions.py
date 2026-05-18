"""
Travel latent dimensional spaces — Push-Pull Motivation Theory, v1 core 12.

PUSH = intrinsic motivations (why someone travels) — 6 dims.
PULL = destination/experience attributes they want — 6 dims.

Used by module3_persona._score_dimension_set: each keyword is substring-matched
against persona text; hit density → dimension score. Keep keywords discriminating
and phrase-anchored — generic single words create cross-dimension noise.

Each dimension is unipolar (positive presence). Bipolar concepts (e.g. introvert
vs. extrovert sociality) emerge compositionally across dimensions rather than
via dedicated negative axes.

Budget and pace are structured constraints on TripConstraints (budget_usd,
pace), not latent dimensions — they don't need to be mined from free text.

Owned by Jahnvi. Module3 reads these without hardcoding dimension names.
"""

# ── PUSH: why they travel (6) ─────────────────────────────────────────────────

PUSH_DIMENSIONS: dict[str, list[str]] = {
    "escape_reset": [
        # Detachment from current life + physical/mental recovery.
        "disconnect", "off the grid", "unplug", "switch off",
        "leave behind", "leave it all", "leave everything", "drop everything",
        "no emails", "no work", "out of routine",
        "away from", "get away", "step away", "break from",
        "obligations behind", "responsibilities behind",
        "everyday life", "day-to-day", "monotony", "the grind",
        "same four walls", "change of scenery", "escape reality",
        "need a break", "no responsibilities",
        "exhausted", "burnout", "burnt out",
        "drained", "depleted", "run down", "worn out", "at capacity",
        "recharge", "recover", "recuperate", "decompress",
        "sleep in", "lie in", "late mornings", "long breakfasts",
        "nap", "lazy", "lounging", "hammock",
        "unwind", "slow down", "do nothing", "no clock", "offline",
        "mentally exhausted",
    ],
    "adventure_novelty": [
        # Push myself, risk, spontaneity, first-time.
        "feel alive", "push myself", "challenge myself", "take a risk",
        "adrenaline", "thrill",
        "out of comfort zone", "push boundaries",
        "heart racing", "excited and scared",
        "make it up as we go", "wing it", "last minute",
        "take the plunge", "jump in", "go for it",
        "first time", "never done before", "new territory",
        "rough it", "uncharted",
    ],
    "connection": [
        # Travel together — companions or partner; quality time / shared memories.
        "share", "bond", "quality time", "be present with",
        "memories with", "making memories", "shared experience",
        "inside joke", "catch up", "reconnect",
        "get closer", "strengthen", "bonding",
        "long overdue trip", "finally do this", "been meaning to",
        "with the people i love", "loved ones",
        "the whole family", "family trip", "couples trip",
        "friends trip", "reunion",
        "romantic", "intimate", "anniversary", "honeymoon",
        "candlelit", "just us", "just us two", "us time", "couple time",
        "my partner", "my boyfriend", "my girlfriend",
        "my husband", "my wife", "fiancé", "fiancée", "other half",
        "date night", "sunset together", "slow mornings together",
        "reconnect as a couple", "reignite", "rekindle",
        "our place", "privacy",
    ],
    "reflection": [
        # Think clearly, perspective, identity processing.
        "reflect", "process", "perspective", "clarity",
        "think clearly", "alone with my thoughts", "figure out",
        "introspect", "journal", "meditate on", "sit with",
        "what matters", "what i want", "where i'm going",
        "reassess", "recalibrate", "ground myself", "centre myself",
        "see things differently", "new eyes", "opened my mind",
        "blank slate", "press reset", "press pause", "step back",
        "start fresh", "clear my mind",
        "new chapter", "life transition",
    ],
    "curiosity": [
        # Intellectual stimulation, want to understand.
        "curious", "fascinated", "intrigued", "want to know",
        "make sense of", "go deeper",
        "story behind", "significance",
        "beyond the guidebook", "intellectually stimulating",
        "the real", "true picture", "nuance",
        "how people live", "different ways of",
        "worldview", "read about", "background",
    ],
    "prestige_reward": [
        # Bucket list / earned / once-in-a-lifetime.
        # Note: contains both milestone-marking and status-signaling clusters;
        # may split into prestige_milestone / prestige_status in v2.
        "dream trip", "once in a lifetime", "earned this", "deserved",
        "bucket list", "milestone", "anniversary trip",
        "unforgettable", "memorable trip",
        "treat myself", "worked hard for this",
        "splurge", "spare no expense", "go all out",
        "the best of the best", "top tier", "no compromises",
        "do it properly", "do it right",
        "instagram worthy", "bragging rights", "tell this story",
        "iconic", "legendary",
        "must see", "been dreaming",
        "always wanted to", "on my list for years", "finally",
    ],
}

# ── PULL: what they want at the destination (6) ───────────────────────────────

PULL_DIMENSIONS: dict[str, list[str]] = {
    "nature_outdoors": [
        # Landscape + outdoor activity merged — was always one dim split in two.
        "beach", "mountain", "ocean", "forest", "wildlife",
        "coast", "island", "lake", "river",
        "sunrise", "sunset", "fresh air",
        "hiking trail", "national park", "jungle", "rainforest",
        "desert", "glacier", "waterfall", "canyon", "valley",
        "reef", "coral", "fjord",
        "vineyard", "countryside", "remote", "untouched", "pristine",
        "dramatic landscape", "incredible views", "breathtaking views",
        "hike", "trek", "climb", "dive", "surf",
        "kayak", "cycle", "ski", "snowboard", "snorkel",
        "raft", "paraglide", "bungee", "zip line", "abseil",
        "via ferrata", "canyoning",
        "mountain biking", "trail running", "wild swimming",
        "freediving", "windsurf", "kitesurf", "paddleboard",
        "sailing", "yacht charter",
        "rock climbing", "bouldering", "base jump", "skydive",
        "hot air balloon", "horse riding",
        "safari drive", "game drive",
        "summit", "altitude",
    ],
    "culture_history": [
        "museum", "history", "architecture", "heritage",
        "temple", "gallery", "monument", "old town", "ruins",
        "ceremony", "ritual", "ancient", "medieval", "colonial",
        "sacred", "spiritual", "mythology", "folklore",
        "festival", "performance", "theatre", "opera",
        "classical music", "indigenous", "tribal",
        "archaeological", "world heritage", "unesco",
        "bazaar", "souk", "artisan", "handmade", "traditional craft",
        "pottery", "weaving", "sculpture", "street art", "mural",
        "exhibition", "guided tour", "local guide",
    ],
    "food_drink": [
        "restaurant", "cuisine", "street food",
        "chef", "culinary", "local food",
        "wine", "coffee", "tasting menu", "michelin", "fine dining",
        "hole in the wall", "local canteen", "home cooked",
        "farm to table", "seasonal produce",
        "food tour", "cooking class", "food market", "night market",
        "hawker",
        "ramen", "tacos", "pasta", "curry", "sushi", "tapas", "mezze",
        "charcuterie", "seafood", "vegetarian", "vegan",
        "craft beer", "winery", "brewery", "distillery", "sake",
        "tea ceremony", "unforgettable meal",
    ],
    "nightlife_social": [
        # Nightlife + atmosphere/sociality merged. v2 may split warm-conviviality
        # (long-Italian-lunch register) from bass-in-your-chest party energy.
        "nightclub", "dance floor", "rooftop bar", "speakeasy",
        "live music", "concert", "gig", "dj set",
        "techno", "house music", "afrobeats", "rave", "underground",
        "club scene", "party district",
        "bar hop", "pub crawl", "night out",
        "after dark", "city that never sleeps", "buzzing",
        "happy hour", "cocktail bar",
        "lively", "buzz", "atmosphere", "social scene",
        "meet people", "crowded", "conversation",
        "community", "strangers", "shared tables",
        "busy café", "people everywhere", "communal",
        "bustling", "vibrant", "packed",
        "where everyone is", "the place to be",
        "communal table", "bar seat",
        "around people", "humming with",
        "friendly", "welcoming", "chatty", "good crowd",
        "people lingering", "family-style", "everyone talking",
        "easy to meet people",
    ],
    "comfort_luxury": [
        # Friction-avoidance + premium service merged. A backpacker can want
        # comfort without luxury; v2 may re-split if real vectors diverge.
        "easy", "convenient", "stress-free", "seamless",
        "walkable", "comfortable", "cozy",
        "familiar", "reliable", "smooth", "no hassle",
        "direct flight", "central location",
        "good bed", "room service",
        "easy transit", "walking distance",
        "english spoken", "predictable",
        "accessible", "well-located", "no surprises",
        "easy to navigate", "simple", "straightforward",
        "don't want to think", "taken care of",
        "luxury", "five star", "5 star", "boutique hotel", "exclusive",
        "high-end", "concierge", "champagne",
        "suite", "villa", "fine dining",
        "first class", "business class", "private jet",
        "yacht", "overwater bungalow", "infinity pool",
        "butler", "white glove", "impeccable service",
        "luxury resort", "spa resort", "design hotel",
        "heritage hotel", "palace hotel",
        "private beach", "private pool", "personal chef",
        "bespoke", "curated experience", "private tour",
        "skip the queue", "vip access",
        "the best table", "the best room", "upgrade",
    ],
    "exploration_local": [
        # Wandering + anti-tourist merged. v2 may split process (wander/get lost)
        # from preference (no crowds / locals only).
        "explore", "wander", "stumble", "get lost",
        "follow my nose", "see where it goes", "no destination",
        "happen to find",
        "discovered by accident", "wasn't expecting",
        "surprised by", "turn down a random street",
        "make it up", "see what happens",
        "hidden", "off the beaten path", "secret",
        "no tourists", "not in the guidebook", "locals only",
        "away from crowds", "overlooked", "underrated",
        "lesser known", "not on the map", "under the radar",
        "tucked away", "down a side street",
        "crowd-free", "not many people know about",
        "insider tip", "insider knowledge",
        "hidden gem", "hole in the wall",
        "where locals go", "ask a local",
    ],
}

ALL_DIMENSIONS: dict[str, list[str]] = {**PUSH_DIMENSIONS, **PULL_DIMENSIONS}
