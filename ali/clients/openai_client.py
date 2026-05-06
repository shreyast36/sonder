from ali.clients.base import BaseLLMClient
from shared.schemas import ModelTier
from shared.config import OPENAI_API_KEY, SMALL_MODEL_NAME, LARGE_MODEL_NAME


class OpenAISmallClient(BaseLLMClient):
    """
    OpenAI client for the SMALL model tier.
    Ali: set SMALL_MODEL_PROVIDER=openai and SMALL_MODEL_NAME=<your chosen model> in .env.

    Good for: chat topics, persona labels, quick edits, notification messages.
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
        # TODO: call openai.AsyncOpenAI(api_key=OPENAI_API_KEY).chat.completions.create(...)
        raise NotImplementedError

    async def stream(self, prompt: str, system: str = ""):
        # TODO: stream=True, yield chunk.choices[0].delta.content
        raise NotImplementedError


class OpenAILargeClient(BaseLLMClient):
    """
    OpenAI client for the LARGE model tier.
    Ali: set LARGE_MODEL_PROVIDER=openai and LARGE_MODEL_NAME=<your chosen model> in .env.

    Good for: full itinerary generation, complex refinements, what-if recommendations.
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
        # TODO: implement
        raise NotImplementedError

    async def stream(self, prompt: str, system: str = ""):
        # TODO: implement
        raise NotImplementedError
