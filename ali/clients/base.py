from abc import ABC, abstractmethod
from typing import AsyncIterator
from shared.schemas import ModelTier


class BaseLLMClient(ABC):
    """
    Abstract base class all LLM provider clients must implement.
    Ali decides which concrete class maps to which tier in the routing engine.

    Example usage (from routing/engine.py):
        client = OpenAIClient()
        response = await client.complete(prompt="Generate a 5-day itinerary...", system="You are a travel planner.")
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The model identifier string used in API calls. Set by each subclass."""
        ...

    @property
    @abstractmethod
    def tier(self) -> ModelTier:
        """Which tier this client belongs to: small | large."""
        ...

    @property
    @abstractmethod
    def cost_per_1k_input_tokens(self) -> float:
        """Approximate USD cost per 1000 input tokens. Used by the routing engine."""
        ...

    @abstractmethod
    async def complete(self, prompt: str, system: str = "", max_tokens: int = 2048) -> str:
        """
        Single-turn completion. Returns the full response as a string.

        Expected input:
            prompt     = "Generate a 5-day itinerary for Bali for a relaxed couple..."
            system     = "You are an expert travel planner. Output valid JSON."
            max_tokens = 2048

        Expected output:
            '{"days": [{"day_number": 1, "activities": [...]}]}'
        """
        ...

    @abstractmethod
    async def stream(self, prompt: str, system: str = "") -> AsyncIterator[str]:
        """
        Streaming completion. Yields token chunks as they arrive.
        Used by itinerary_generator.py to stream tokens to Mushahid's SSE layer.

        Expected usage:
            async for chunk in client.stream(prompt, system):
                yield chunk  # forward to SSE
        """
        ...


def scaffold_review() -> None:
    """
    Ali — BaseLLMClient was pre-populated as scaffold. Review the abstract interface
    before building any concrete clients on top of it. Add any additional methods
    your provider clients will need (e.g. count_tokens, health_check). Delete this
    function when the interface is finalised.
    """
    raise NotImplementedError
