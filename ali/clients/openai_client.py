import openai
from ali.clients.base import BaseLLMClient
from shared.schemas import ModelTier
from shared.config import OPENAI_API_KEY, SMALL_MODEL_NAME, LARGE_MODEL_NAME

_client: openai.AsyncOpenAI | None = None


def _get_client() -> openai.AsyncOpenAI:
    global _client
    if _client is None:
        _client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _client


class OpenAISmallClient(BaseLLMClient):
    """
    OpenAI client for the SMALL model tier.
    Ali: set SMALL_MODEL_PROVIDER=openai and SMALL_MODEL_NAME=gpt-4o-mini in .env.

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
        return 0.000150  # gpt-4o-mini: $0.150 per 1M input tokens

    async def complete(self, prompt: str, system: str = "", max_tokens: int = 512) -> str:
        response = await _get_client().chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=max_tokens,
        )
        return response.choices[0].message.content

    async def stream(self, prompt: str, system: str = ""):
        async with _get_client().chat.completions.stream(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        ) as stream:
            async for text in stream.text_stream:
                yield text


class OpenAILargeClient(BaseLLMClient):
    """
    OpenAI client for the LARGE model tier.
    Ali: set LARGE_MODEL_PROVIDER=openai and LARGE_MODEL_NAME=gpt-4o in .env.

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
        return 0.002500  # gpt-4o: $2.50 per 1M input tokens

    async def complete(self, prompt: str, system: str = "", max_tokens: int = 16384) -> str:
        response = await _get_client().chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=max_tokens,
        )
        return response.choices[0].message.content

    async def stream(self, prompt: str, system: str = ""):
        async with _get_client().chat.completions.stream(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        ) as stream:
            async for text in stream.text_stream:
                yield text
