"""
Travel latent dimensional spaces based on Push-Pull Motivation Theory.

PUSH = intrinsic motivations (why someone travels).
PULL = destination/experience attributes they want.

Used by module3_persona._score_dimension_set: each keyword is substring-matched
against persona text; hit density → dimension score. Keep keywords discriminating
and phrase-anchored — generic single words create cross-dimension noise.

Each dimension is unipolar (positive presence). Bipolar concepts (e.g.
social_energy vs. solitude) emerge compositionally across dimensions
rather than via dedicated negative axes.

Owned by Jahnvi. Module3 reads these without hardcoding dimension names.
"""

# ── PUSH: why they travel ─────────────────────────────────────────────────────

PUSH_DIMENSIONS: dict[str, list[str]] = {
    "escape": [
        # Literal detachment from current life/obligations.
        "disconnect", "off the grid", "unplug", "switch off",
        "leave behind", "leave it all", "leave everything", "drop everything",
        "no emails", "no work", "out of routine",
        "away from", "get away", "step away", "break from",
        "obligations behind", "responsibilities behind",
        "everyday life", "day-to-day", "monotony", "the grind",
        "same four walls", "change of scenery", "escape reality",
        "need a break", "no responsibilities",
    ],
    "rest": [
        # Physical/mental recovery — exhaustion → replenishment.
        "exhausted", "burnout", "burnt out",
        "drained", "depleted", "run down", "worn out", "at capacity",
        "recharge", "recover", "recuperate", "decompress",
        "sleep in", "lie in", "late mornings", "long breakfasts",
        "nap", "lazy", "lounging", "hammock",
        "unwind", "slow down", "do nothing", "do nothing days",
        "no clock", "offline", "mentally exhausted",
    ],
    "adventure_seeking": [
        # Push myself, risk, spontaneity.
        "feel alive", "push myself", "challenge myself", "take a risk",
        "adrenaline", "thrill",
        "out of comfort zone", "push boundaries",
        "heart racing", "excited and scared",
        "make it up as we go", "wing it", "last minute",
        "take the plunge", "jump in", "go for it",
        "first time", "never done before", "new territory",
        "rough it", "uncharted",
    ],
    "social_bonding": [
        # Travel together / connection with companions.
        "share", "bond", "quality time", "be present with",
        "memories with", "making memories", "shared experience",
        "inside joke", "catch up", "reconnect",
        "get closer", "strengthen", "bonding",
        "long overdue trip", "finally do this", "been meaning to",
        "with the people i love", "loved ones",
        "the whole family", "family trip", "couples trip",
        "friends trip", "reunion",
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
    "romance": [
        # Couple / intimate.
        "romantic", "intimate", "anniversary", "honeymoon",
        "candlelit", "just us", "just us two", "us time", "couple time",
        "my partner", "my boyfriend", "my girlfriend",
        "my husband", "my wife", "fiancé", "fiancée", "other half",
        "date night", "sunset together", "slow mornings together",
        "reconnect as a couple", "reignite", "rekindle",
        "our place", "privacy",
    ],
    "prestige": [
        # Bucket list / earned / once-in-a-lifetime.
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

# ── PULL: what they want at the destination ───────────────────────────────────

PULL_DIMENSIONS: dict[str, list[str]] = {
    "nature": [
        "beach", "mountain", "ocean", "forest", "wildlife",
        "coast", "island", "lake", "river",
        "sunrise", "sunset", "fresh air",
        "hiking trail", "national park", "jungle", "rainforest",
        "desert", "glacier", "waterfall", "canyon", "valley",
        "reef", "coral", "fjord",
        "vineyard", "countryside", "remote", "untouched", "pristine",
        "dramatic landscape", "incredible views", "breathtaking views",
    ],
    "culture": [
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
    "food": [
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
    "nightlife": [
        "nightclub", "dance floor", "rooftop bar", "speakeasy",
        "live music", "concert", "gig", "dj set",
        "techno", "house music", "afrobeats", "rave", "underground",
        "club scene", "party district",
        "bar hop", "pub crawl", "night out",
        "after dark", "city that never sleeps", "buzzing",
        "happy hour", "cocktail bar",
    ],
    "wellness": [
        "spa", "yoga", "retreat", "massage",
        "mindfulness", "meditation",
        "wellness", "detox", "healing", "therapeutic",
        "ayurveda", "sound bath", "breathwork",
        "float tank", "cold plunge", "sauna", "hammam",
        "hot spring", "thermal bath", "herbal remedy",
        "reiki", "acupuncture", "reflexology", "aromatherapy",
        "digital detox", "no screens",
        "restorative yoga", "pilates", "tai chi", "qi gong",
    ],
    "outdoor_activity": [
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
    "luxury": [
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
    "budget": [
        "budget", "affordable", "cheap", "hostel", "backpack",
        "economical", "stretch the budget",
        "cheap eats", "local transport", "walk everywhere",
        "free entry", "free museum",
        "dormitory", "guesthouse", "homestay", "couchsurf",
        "self catering", "street food only",
        "avoid tourist trap", "overpriced",
        "budget airline", "overnight bus", "overnight train",
        "shoestring", "frugal",
    ],
    "exploration": [
        # Wander, get lost, serendipity.
        "explore", "wander", "stumble", "get lost",
        "follow my nose", "see where it goes", "no destination",
        "happen to find",
        "discovered by accident", "wasn't expecting",
        "surprised by", "turn down a random street",
        "make it up", "see what happens",
    ],
    "anti_tourist": [
        # Avoid crowds, locals only, hidden.
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
    "comfort_seeking": [
        # Friction avoidance, ease, predictability.
        "easy", "convenient", "stress-free", "seamless",
        "walkable", "comfortable", "cozy",
        "familiar", "reliable", "smooth", "no hassle",
        "direct flight", "central location",
        "good bed", "room service",
        "easy transit", "walking distance",
        "english spoken", "predictable",
        "accessible", "well-located",
        "no surprises",
    ],
    "social_energy": [
        # Lively, around people, atmosphere (unipolar positive).
        "lively", "buzz", "atmosphere", "social scene",
        "meet people", "crowded", "conversation",
        "community", "strangers", "shared tables",
        "busy café", "people everywhere", "communal",
        "bustling", "vibrant", "packed",
        "where everyone is", "the place to be",
        "communal table", "bar seat",
        "around people", "humming with",
    ],
    "photography": [
        # Visual capture / aesthetic documentation.
        "photograph", "photography", "camera",
        "golden hour", "blue hour", "magic hour",
        "long exposure", "landscape photography", "street photography",
        "candid shot", "composition", "bokeh",
        "lightroom", "mirrorless", "dslr",
        "35mm", "polaroid", "drone footage",
        "wide angle", "telephoto",
        "postcard view", "cinematic shot", "visual storytelling",
    ],
}

# ── Pace signals ──────────────────────────────────────────────────────────────

PACE_SIGNALS: dict[str, list[str]] = {
    "relaxed": [
        "slow", "leisurely", "linger", "unhurried",
        "no rush",
        "quiet mornings", "take our time", "nowhere to be",
        "drift", "meander", "amble",
        "stay a while", "settle", "sink in",
        "quality over quantity", "depth not breadth",
        "fewer places", "really get to know",
        "long lunches", "slow afternoons",
        "evenings with no plan", "follow our mood",
        "let it unfold",
    ],
    "packed": [
        "packed", "fast-paced", "fit in", "see everything",
        "full day", "non-stop", "back to back",
        "tight schedule", "hit all the highlights",
        "cover a lot of ground", "multiple cities",
        "day trips", "excursions",
        "make the most of", "every minute",
        "5am start", "first bus", "last bus",
        "long days", "hit the ground running",
        "researched everything", "plan every day",
    ],
}

ALL_DIMENSIONS: dict[str, list[str]] = {**PUSH_DIMENSIONS, **PULL_DIMENSIONS}
