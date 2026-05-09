import logging
from ali.routing.classifier import classify
from ali.clients.base import BaseLLMClient
from shared.schemas import ModelTier
from shared.config import SMALL_MODEL_PROVIDER, LARGE_MODEL_PROVIDER

logger = logging.getLogger(__name__)


def get_client(tier: ModelTier) -> BaseLLMClient:
    """
    Return the appropriate LLM client for the given tier.
    Provider is set via SMALL_MODEL_PROVIDER / LARGE_MODEL_PROVIDER in .env.

    Expected input:  ModelTier.large
    Expected output: the correct BaseLLMClient subclass for the provider
    """
    provider = SMALL_MODEL_PROVIDER if tier == ModelTier.small else LARGE_MODEL_PROVIDER
    return _get_client_for_provider(tier, provider)


# Fallback chain: if primary client fails, try these in order per tier.
_FALLBACKS: dict[ModelTier, list] = {
    ModelTier.small: ["deepseek", "openai"],
    ModelTier.large: ["deepseek", "openai"],
}


def _get_client_for_provider(tier: ModelTier, provider: str) -> BaseLLMClient:
    from ali.clients.deepseek_client import DeepSeekSmallClient, DeepSeekLargeClient
    from ali.clients.openai_client import OpenAISmallClient, OpenAILargeClient
    from ali.clients.anthropic_client import AnthropicLargeClient

    if provider == "deepseek":
        return DeepSeekSmallClient() if tier == ModelTier.small else DeepSeekLargeClient()
    if provider == "openai":
        return OpenAISmallClient() if tier == ModelTier.small else OpenAILargeClient()
    if provider == "anthropic":
        return AnthropicLargeClient()
    raise ValueError(f"Unsupported provider '{provider}'")


async def route_request(task_type: str, prompt: str, system: str = "", context: dict = {}) -> str:
    """
    Route a task to the right model and return the full response string.
    Falls back to the next provider in the tier if the primary fails.
    """
    tier = classify(task_type, context)
    providers = _FALLBACKS.get(tier, [])

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


async def stream_request(task_type: str, prompt: str, system: str = "", context: dict = {}):
    """
    Streaming version of route_request. Yields raw token strings.
    Falls back to the next provider in the tier if the primary fails.
    """
    tier = classify(task_type, context)
    providers = _FALLBACKS.get(tier, [])

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
