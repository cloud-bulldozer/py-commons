"""
commons.inference - LLM Inference Client

Client for OpenAI-compatible inference endpoints with support for
tool calling and agentic loops.
"""

from .client import (
    InferenceClient,
    analyze_with_agentic,
    get_inference_client,
    get_inference_config,
)

from .exceptions import (
    InferenceClientError,
    InferenceAPIError,
    InferenceIterationLimitError,
)

from .constants import (
    INFERENCE_TEMPERATURE,
    INFERENCE_MAX_TOKENS,
    INFERENCE_MAX_TOOL_ITERATIONS,
    INFERENCE_API_TIMEOUT,
)

__all__ = [
    "InferenceClient",
    "analyze_with_agentic",
    "get_inference_client",
    "get_inference_config",
    "InferenceClientError",
    "InferenceAPIError",
    "InferenceIterationLimitError",
    "INFERENCE_TEMPERATURE",
    "INFERENCE_MAX_TOKENS",
    "INFERENCE_MAX_TOOL_ITERATIONS",
    "INFERENCE_API_TIMEOUT",
]
