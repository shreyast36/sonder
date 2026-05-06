from ali.clients.base import BaseLLMClient
from shared.schemas import ModelTier
from shared.config import GOOGLE_API_KEY, LARGE_MODEL_NAME


class GoogleLargeClient(BaseLLMClient):
    """
    Google Generative AI client for the LARGE model tier.
    Ali: set LARGE_MODEL_PROVIDER=google and LARGE_MODEL_NAME=<your chosen model> in .env.

    Good for: long-context itinerary generation, multi-user conflict resolution.
    """

    @property
    def model_name(self) -> str:
        return LARGE_MODEL_NAME

    @property
    def tier(self) -> ModelTier:
        return ModelTier.large

    @property
    def cost_per_1k_input_tokens(self) -> float:
        # TODO: set based on your chosen model's pricing
        raise NotImplementedError

    async def complete(self, prompt: str, system: str = "", max_tokens: int = 4096) -> str:
        # TODO: call google.generativeai with GOOGLE_API_KEY and LARGE_MODEL_NAME
        raise NotImplementedError

    async def stream(self, prompt: str, system: str = ""):
        # TODO: use generate_content_async with stream=True
        raise NotImplementedError
