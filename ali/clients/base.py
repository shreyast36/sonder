# TODO: Ali — abstract base class for all LLM clients.
# All clients must implement:
#   complete(prompt: str, system: str, max_tokens: int) → str
#   stream(prompt: str, system: str) → AsyncIterator[str]
# Expose model name, tier (SMALL | LARGE | VALIDATOR), and cost per 1k tokens.
