from ali.clients.base import BaseLLMClient
from shared.schemas import ModelTier
from shared.config import GROQ_API_KEY, SMALL_MODEL_NAME


class GroqSmallClient(BaseLLMClient):
    """
    Groq client for the SMALL model tier — extremely fast inference.
    Ali: set SMALL_MODEL_PROVIDER=groq and SMALL_MODEL_NAME=<your chosen model> in .env.

    Good for: chat topics, icebreakers, persona labels — anything latency-sensitive.
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
        # TODO: call groq.AsyncGroq(api_key=GROQ_API_KEY).chat.completions.create(...)
        raise NotImplementedError

    async def stream(self, prompt: str, system: str = ""):
        # TODO: stream=True, yield chunks
        raise NotImplementedError
