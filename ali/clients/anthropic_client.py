from ali.clients.base import BaseLLMClient
from shared.schemas import ModelTier
from shared.config import ANTHROPIC_API_KEY, LARGE_MODEL_NAME


class AnthropicLargeClient(BaseLLMClient):
    """
    Anthropic client for the LARGE model tier.
    Ali: set LARGE_MODEL_PROVIDER=anthropic and LARGE_MODEL_NAME=<your chosen model> in .env.

    Good for: itinerary generation, RAG explanations, multi-user conflict resolution.
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
        # TODO: call anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY).messages.create(...)
        raise NotImplementedError

    async def stream(self, prompt: str, system: str = ""):
        # TODO: use .stream() context manager, yield text chunks
        raise NotImplementedError
