import openai
from ali.clients.base import BaseLLMClient
from shared.schemas import ModelTier
from shared.config import DEEPSEEK_API_KEY, SMALL_MODEL_NAME, LARGE_MODEL_NAME

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class DeepSeekSmallClient(BaseLLMClient):
    """
    DeepSeek client for the SMALL model tier.
    Set SMALL_MODEL_PROVIDER=deepseek and SMALL_MODEL_NAME=deepseek-chat in .env.
    """

    @property
    def model_name(self) -> str:
        return SMALL_MODEL_NAME

    @property
    def tier(self) -> ModelTier:
        return ModelTier.small

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.000270  # deepseek-chat: $0.27 per 1M input tokens (cache miss)

    async def complete(self, prompt: str, system: str = "", max_tokens: int = 512) -> str:
        client = openai.AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        response = await client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    async def stream(self, prompt: str, system: str = ""):
        client = openai.AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        response = await client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            stream=True,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class DeepSeekLargeClient(BaseLLMClient):
    """
    DeepSeek client for the LARGE model tier.
    Set LARGE_MODEL_PROVIDER=deepseek and LARGE_MODEL_NAME=deepseek-chat in .env.
    """

    @property
    def model_name(self) -> str:
        return LARGE_MODEL_NAME

    @property
    def tier(self) -> ModelTier:
        return ModelTier.large

    @property
    def cost_per_1k_input_tokens(self) -> float:
        return 0.000270  # deepseek-chat: $0.27 per 1M input tokens (cache miss)

    async def complete(self, prompt: str, system: str = "", max_tokens: int = 4096) -> str:
        client = openai.AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        response = await client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    async def stream(self, prompt: str, system: str = ""):
        client = openai.AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        response = await client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            stream=True,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
