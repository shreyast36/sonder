import logging
from ali.routing.classifier import classify
from ali.clients.base import BaseLLMClient
from shared.schemas import ModelTier
from shared.config import SMALL_MODEL_PROVIDER, LARGE_MODEL_PROVIDER

logger = logging.getLogger(__name__)

# Providers tried after the configured primary fails, in order.
_FALLBACK_ORDER = ["deepseek", "openai", "anthropic"]


def _build_provider_list(tier: ModelTier) -> list[str]:
    primary = SMALL_MODEL_PROVIDER if tier == ModelTier.small else LARGE_MODEL_PROVIDER
    return [primary] + [p for p in _FALLBACK_ORDER if p != primary]


def get_client(tier: ModelTier) -> BaseLLMClient:
    """Return the configured primary client for the given tier."""
    provider = SMALL_MODEL_PROVIDER if tier == ModelTier.small else LARGE_MODEL_PROVIDER
    return _get_client_for_provider(tier, provider)


def _get_client_for_provider(tier: ModelTier, provider: str) -> BaseLLMClient:
    from ali.clients.deepseek_client import DeepSeekSmallClient, DeepSeekLargeClient
    from ali.clients.openai_client import OpenAISmallClient, OpenAILargeClient
    from ali.clients.anthropic_client import AnthropicLargeClient

    if provider == "deepseek":
        return DeepSeekSmallClient() if tier == ModelTier.small else DeepSeekLargeClient()
    if provider == "openai":
        return OpenAISmallClient() if tier == ModelTier.small else OpenAILargeClient()
    if provider == "anthropic":
        if tier == ModelTier.small:
            raise ValueError("Anthropic has no small-tier client — choose deepseek or openai for SMALL_MODEL_PROVIDER")
        return AnthropicLargeClient()
    raise ValueError(f"Unsupported provider '{provider}'")


async def route_request(task_type: str, prompt: str, system: str = "", context: dict | None = None) -> str:
    """
    Route a task to the right model and return the full response string.
    Starts with the configured primary provider, falls back to others on failure.
    """
    tier = classify(task_type, context)
    providers = _build_provider_list(tier)

    last_exc: Exception = RuntimeError("No providers configured")
    for provider in providers:
        try:
            client = _get_client_for_provider(tier, provider)
            return await client.complete(prompt, system)
        except ValueError:
            continue
        except Exception as exc:
            logger.warning("Provider %s failed for task %s: %s", provider, task_type, exc)
            last_exc = exc

    raise last_exc


async def stream_request(task_type: str, prompt: str, system: str = "", context: dict | None = None):
    """
    Streaming version of route_request. Yields raw token strings.
    Starts with the configured primary provider, falls back to others on failure.
    """
    tier = classify(task_type, context)
    providers = _build_provider_list(tier)

    for provider in providers:
        try:
            client = _get_client_for_provider(tier, provider)
            async for chunk in client.stream(prompt, system):
                yield chunk
            return
        except ValueError:
            continue
        except Exception as exc:
            logger.warning("Streaming provider %s failed for task %s: %s", provider, task_type, exc)

    raise RuntimeError(f"All providers failed for task '{task_type}'")
