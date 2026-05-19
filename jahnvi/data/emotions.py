"""
GoEmotions taxonomy — 27 fine-grained emotion labels with one-line glosses.

Source: Demszky et al. (2020), "GoEmotions: A Dataset of Fine-Grained Emotions"
        https://arxiv.org/abs/2005.00547

We don't ship the 58k labeled training rows. We use the label vocabulary as
anchor vectors: each label's gloss is embedded once via the same OpenAI 1536-
dim model that powers the rest of the persona pipeline, and the user's free
text is classified by cosine similarity against those anchors.

The glosses below are deliberately short and tone-anchored — they're meant
to make the embedding space crisp, not to read like dictionary definitions.
"""

GOEMOTIONS_LABELS: dict[str, str] = {
    "admiration":     "finding someone or something genuinely impressive and worthy of respect",
    "amusement":      "lightly entertained, finding something funny or playful",
    "anger":          "feeling strong displeasure, indignation, or hostility",
    "annoyance":      "low-grade irritation, mild bother, exasperation",
    "approval":       "endorsing, agreeing with, or signalling support for something",
    "caring":         "warmth and tenderness toward someone's wellbeing",
    "confusion":      "lack of clarity, uncertainty, struggling to make sense of something",
    "curiosity":      "wanting to know more, drawn toward understanding something new",
    "desire":         "longing for something, wanting it deeply",
    "disappointment": "let down, hopes unmet, a softer sadness about an outcome",
    "disapproval":    "rejecting or pushing back against something",
    "disgust":        "strong distaste, revulsion, finding something repellent",
    "embarrassment":  "self-conscious discomfort, awkwardness about oneself",
    "excitement":     "energetic anticipation, looking forward eagerly",
    "fear":           "apprehension or anxiety about something threatening",
    "gratitude":      "thankfulness, appreciation for what one has received",
    "grief":          "deep sorrow from real loss",
    "joy":            "uplifted pleasure, lightness, real happiness",
    "love":           "deep affection, devotion, abiding warmth toward someone",
    "nervousness":    "uneasy anticipation, butterflies before something uncertain",
    "optimism":       "hopeful expectation that good things will come",
    "pride":          "satisfaction from one's own effort, achievement, or identity",
    "realization":    "a quiet click — coming to understand something",
    "relief":         "release from a weight, no longer worried",
    "remorse":        "regret over having caused harm, wishing to undo",
    "sadness":        "general melancholy, low feeling, sorrow",
    "surprise":       "unexpected jolt, something out of nowhere",
}

ALL_EMOTIONS: list[str] = list(GOEMOTIONS_LABELS.keys())
