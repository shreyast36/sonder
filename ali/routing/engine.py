from ali.routing.classifier import classify
from ali.clients.base import BaseLLMClient
from shared.schemas import ModelTier
from shared.config import (
    SMALL_MODEL_PROVIDER, LARGE_MODEL_PROVIDER, VALIDATOR_MODEL_PROVIDER
)


def get_client(tier: ModelTier) -> BaseLLMClient:
    """
    Return the appropriate LLM client for a given tier, based on provider config.

    Ali: the provider is set via env vars (SMALL_MODEL_PROVIDER, LARGE_MODEL_PROVIDER,
    VALIDATOR_MODEL_PROVIDER). Add fallback logic here if a provider is unavailable.

    Expected input:  ModelTier.large
    Expected output: the correct BaseLLMClient subclass for the given tier and provider
    """
    if tier == ModelTier.small:
        provider = SMALL_MODEL_PROVIDER
    elif tier == ModelTier.large:
        provider = LARGE_MODEL_PROVIDER
    else:
        provider = VALIDATOR_MODEL_PROVIDER

    # TODO: import and return the correct client class based on (provider, tier)
    # Add a case for each provider you decide to support.
    raise NotImplementedError


async def route_request(task_type: str, prompt: str, system: str = "", context: dict = {}) -> str:
    """
    Route a task to the right model and return the response.
    This is the single entry point Ali exposes to the rest of the system.

    Expected input:
        task_type = "itinerary_generation"
        prompt    = "Generate a 5-day itinerary for Bali for a relaxed couple with $2000 budget..."
        system    = "You are an expert travel planner. Output valid JSON."
        context   = {"token_estimate": 3200}

    Expected output:
        '{"days": [{"day_number": 1, "theme": "Culture & Coastal Views", "activities": [...]}]}'

    Flow:
        1. classify(task_type) → ModelTier
        2. get_client(tier) → BaseLLMClient
        3. client.complete(prompt, system) → str
        4. On failure: retry with next available model in the same tier
    """
    tier   = classify(task_type, context)
    client = get_client(tier)
    # TODO: await client.complete(prompt, system), add retry/fallback logic
    raise NotImplementedError


async def stream_request(task_type: str, prompt: str, system: str = "", context: dict = {}):
    """
    Streaming version of route_request. Yields token chunks.
    Used by itinerary_generator.py → Mushahid's SSE layer.

    Expected usage:
        async for chunk in stream_request("itinerary_generation", prompt, system):
            yield format_event("generating", {"chunk": chunk})
    """
    tier   = classify(task_type, context)
    client = get_client(tier)
    # TODO: async for chunk in client.stream(prompt, system): yield chunk
    raise NotImplementedError
