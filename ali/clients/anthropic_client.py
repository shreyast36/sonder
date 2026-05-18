import anthropic
from ali.clients.base import BaseLLMClient
from shared.schemas import ModelTier
from shared.config import ANTHROPIC_API_KEY, LARGE_MODEL_NAME, SMALL_MODEL_NAME

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _client


class AnthropicSmallClient(BaseLLMClient):
    """
    Anthropic client for the SMALL model tier (e.g. claude-haiku-4-5).
    Used for voice-y short tasks: persona_label, icebreaker, chat_topics.
    """

    @property
    def model_name(self) -> str:
        return SMALL_MODEL_NAME

    @property
    def tier(self) -> ModelTier:
        return ModelTier.small

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.000800  # claude-haiku-4-5: ~$0.80 per 1M input tokens

    async def complete(self, prompt: str, system: str = "", max_tokens: int = 1024) -> str:
        response = await _get_client().messages.create(
            model=self.model_name,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return response.content[0].text

    async def stream(self, prompt: str, system: str = ""):
        async with _get_client().messages.stream(
            model=self.model_name,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
        ) as stream:
            async for text in stream.text_stream:
                yield text


class AnthropicLargeClient(BaseLLMClient):
    """
    Anthropic client for the LARGE model tier.
    Ali: set LARGE_MODEL_PROVIDER=anthropic and LARGE_MODEL_NAME=claude-sonnet-4-5 in .env.

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
        return 0.003000  # claude-sonnet-4-5: $3.00 per 1M input tokens

    async def complete(self, prompt: str, system: str = "", max_tokens: int = 4096) -> str:
        response = await _get_client().messages.create(
            model=self.model_name,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return response.content[0].text

    async def stream(self, prompt: str, system: str = ""):
        async with _get_client().messages.stream(
            model=self.model_name,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
        ) as stream:
            async for text in stream.text_stream:
                yield text
