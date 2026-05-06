import json
import boto3
from ali.clients.base import BaseLLMClient
from shared.config import (
    AWS_REGION,
    BEDROCK_SMALL_MODEL_ID,
    BEDROCK_LARGE_MODEL_ID,
    BEDROCK_VALIDATOR_MODEL_ID,
)
from shared.schemas import ModelTier

# Ali: Bedrock's invoke format varies by model family — you must handle this yourself.
#
# Anthropic Claude family:
#   body = {"anthropic_version": "bedrock-2023-05-31", "max_tokens": 4096,
#           "system": system, "messages": [{"role": "user", "content": prompt}]}
#
# Meta Llama family:
#   body = {"prompt": f"<s>[INST] {system}\n{prompt} [/INST]", "max_gen_len": 4096}
#
# Mistral family:
#   body = {"prompt": f"<s>[INST] {prompt} [/INST]", "max_tokens": 4096}
#
# Check the AWS Bedrock docs for the exact body shape of whichever model ID you set
# in BEDROCK_SMALL_MODEL_ID / BEDROCK_LARGE_MODEL_ID / BEDROCK_VALIDATOR_MODEL_ID.
#
# Streaming: invoke_model_with_response_stream returns an EventStream.
# Each event is event["chunk"]["bytes"] — decode and parse to extract the text delta.
# The delta field name also varies by family ("delta.text" for Claude, "generation" for Llama).


class BedrockSmallClient(BaseLLMClient):
    """
    Bedrock client for the SMALL tier.
    Model ID is set via BEDROCK_SMALL_MODEL_ID in .env.
    """

    tier = ModelTier.small

    def __init__(self):
        self.model_id = BEDROCK_SMALL_MODEL_ID
        self._client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

    async def complete(self, prompt: str, system: str = "") -> str:
        """
        Expected output: raw model response string (same contract as all other clients).

        TODO:
          1. Build the request body for your chosen model family (see format notes above).
          2. response = self._client.invoke_model(modelId=self.model_id, body=json.dumps(body))
          3. Parse response["body"].read() → extract the text field for your model family.
        """
        raise NotImplementedError

    async def stream(self, prompt: str, system: str = ""):
        """
        Yields string chunks.

        TODO:
          1. response = self._client.invoke_model_with_response_stream(modelId=self.model_id, body=...)
          2. for event in response["body"]: chunk = event["chunk"]["bytes"]; yield text delta
        """
        raise NotImplementedError


class BedrockLargeClient(BaseLLMClient):
    """
    Bedrock client for the LARGE tier.
    Model ID is set via BEDROCK_LARGE_MODEL_ID in .env.
    """

    tier = ModelTier.large

    def __init__(self):
        self.model_id = BEDROCK_LARGE_MODEL_ID
        self._client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

    async def complete(self, prompt: str, system: str = "") -> str:
        # TODO: same pattern as BedrockSmallClient.complete
        raise NotImplementedError

    async def stream(self, prompt: str, system: str = ""):
        # TODO: same pattern as BedrockSmallClient.stream
        raise NotImplementedError


class BedrockValidatorClient(BaseLLMClient):
    """
    Bedrock client for the VALIDATOR tier.
    Model ID is set via BEDROCK_VALIDATOR_MODEL_ID in .env.
    """

    tier = ModelTier.validator

    def __init__(self):
        self.model_id = BEDROCK_VALIDATOR_MODEL_ID
        self._client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

    async def complete(self, prompt: str, system: str = "") -> str:
        # TODO: same pattern as BedrockSmallClient.complete
        raise NotImplementedError

    async def stream(self, prompt: str, system: str = ""):
        # TODO: same pattern as BedrockSmallClient.stream
        raise NotImplementedError
