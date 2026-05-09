import anthropic
from ali.clients.base import BaseLLMClient
from shared.schemas import ModelTier
from shared.config import ANTHROPIC_API_KEY, LARGE_MODEL_NAME, VALIDATOR_MODEL_NAME


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
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model=self.model_name,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return response.content[0].text

    async def stream(self, prompt: str, system: str = ""):
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        async with client.messages.stream(
            model=self.model_name,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
        ) as stream:
            async for text in stream.text_stream:
                yield text


class AnthropicValidatorClient(BaseLLMClient):
    """
    Anthropic client for the VALIDATOR model tier (critic mode).
    Ali: set VALIDATOR_MODEL_PROVIDER=anthropic and VALIDATOR_MODEL_NAME=claude-haiku-4-5 in .env.

    Good for: itinerary feasibility checks, constraint scoring, improvement suggestions.
    """

    @property
    def model_name(self) -> str:
        return VALIDATOR_MODEL_NAME

    @property
    def tier(self) -> ModelTier:
        return ModelTier.validator

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.000800  # claude-haiku-4-5: $0.80 per 1M input tokens

    async def complete(self, prompt: str, system: str = "", max_tokens: int = 1024) -> str:
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model=self.model_name,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return response.content[0].text

    async def stream(self, prompt: str, system: str = ""):
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        async with client.messages.stream(
            model=self.model_name,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
        ) as stream:
            async for text in stream.text_stream:
                yield text
