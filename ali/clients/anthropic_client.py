import anthropic
from ali.clients.base import BaseLLMClient
from shared.schemas import ModelTier
from shared.config import ANTHROPIC_API_KEY, ANTHROPIC_SMALL_MODEL, ANTHROPIC_LARGE_MODEL

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
        return ANTHROPIC_SMALL_MODEL

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

    async def complete_with_tools(
        self,
        prompt: str,
        system: str = "",
        push_ids: list[str] | None = None,
        pull_ids: list[str] | None = None,
        max_tokens: int = 1024,
    ) -> str:
        """
        Call the model with a forced tool-use JSON schema that enumerates
        valid dimension IDs for top_push and top_interests. This prevents
        the model from hallucinating IDs not in the allowed lists.
        Returns the tool input as a JSON string.
        """
        import json as _json

        push_schema: dict = {"type": "string"}
        pull_schema: dict = {"type": "string"}
        if push_ids:
            push_schema = {"type": "string", "enum": push_ids}
        if pull_ids:
            pull_schema = {"type": "string", "enum": pull_ids}

        tool = {
            "name": "output_persona",
            "description": "Output the structured persona inference result.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "top_push": {
                        "type": "array",
                        "items": push_schema,
                        "minItems": 1,
                        "maxItems": 6,
                        "description": "1 to 6 PUSH dimension IDs — pick ALL the ones that genuinely apply to this user. Multiple push motivations are common.",
                    },
                    "top_interests": {
                        "type": "array",
                        "items": pull_schema,
                        "minItems": 1,
                        "maxItems": 6,
                        "description": "1 to 6 PULL dimension IDs — pick ALL the ones that genuinely apply. Multiple pull interests are common.",
                    },
                    "descriptor": {"type": "string"},
                    "paragraph": {"type": "string"},
                    "bullets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                },
                "required": ["top_push", "top_interests", "descriptor", "paragraph", "bullets"],
            },
        }

        response = await _get_client().messages.create(
            model=self.model_name,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            tools=[tool],
            tool_choice={"type": "tool", "name": "output_persona"},
            max_tokens=max_tokens,
        )
        # Extract the tool-call input block and return it as a JSON string.
        for block in response.content:
            if block.type == "tool_use" and block.name == "output_persona":
                return _json.dumps(block.input)
        raise ValueError("Anthropic response did not contain expected tool_use block")

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
        return ANTHROPIC_LARGE_MODEL

    @property
    def tier(self) -> ModelTier:
        return ModelTier.large

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.003000  # claude-sonnet-4-6: $3.00 per 1M input tokens

    async def complete(self, prompt: str, system: str = "", max_tokens: int = 16384) -> str:
        response = await _get_client().messages.create(
            model=self.model_name,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return response.content[0].text

    async def stream(self, prompt: str, system: str = ""):
        # Itinerary JSON for a 7-14 day trip easily exceeds 4k tokens.
        # Sonnet 4.6 supports up to 64k output; 16k is a safe ceiling for itineraries.
        async with _get_client().messages.stream(
            model=self.model_name,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=16384,
        ) as stream:
            async for text in stream.text_stream:
                yield text
