from ali.clients.base import BaseLLMClient
from shared.schemas import ModelTier
from shared.config import MISTRAL_API_KEY, SMALL_MODEL_NAME


class MistralSmallClient(BaseLLMClient):
    """
    Mistral client for the SMALL model tier.
    Ali: set SMALL_MODEL_PROVIDER=mistral and SMALL_MODEL_NAME=<your chosen model> in .env.

    Good for: preference parsing, short explanations, simple itinerary edits.
    """

    @property
    def model_name(self) -> str:
        return SMALL_MODEL_NAME

    @property
    def tier(self) -> ModelTier:
        return ModelTier.small

    @property
    def cost_per_1k_input_tokens(self) -> float:
        # TODO: set based on your chosen model's pricing
        raise NotImplementedError

    async def complete(self, prompt: str, system: str = "", max_tokens: int = 512) -> str:
        # TODO: call mistralai client with MISTRAL_API_KEY and SMALL_MODEL_NAME
        raise NotImplementedError

    async def stream(self, prompt: str, system: str = ""):
        # TODO: implement streaming
        raise NotImplementedError
