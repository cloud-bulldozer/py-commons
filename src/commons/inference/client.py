"""Inference client for OpenAI-compatible LLM endpoints."""

import asyncio
import functools
import json
import logging
import os
from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx
from langchain_core.utils.function_calling import convert_to_openai_tool
from openai import APIConnectionError, APITimeoutError, OpenAI
from openai.types.chat import ChatCompletionMessage

from .constants import (
    INFERENCE_TEMPERATURE,
    INFERENCE_MAX_TOKENS,
    INFERENCE_MAX_TOOL_ITERATIONS,
    INFERENCE_API_TIMEOUT,
)
from .exceptions import (
    InferenceAPIError,
    InferenceIterationLimitError,
)

logger = logging.getLogger(__name__)


class InferenceClient:
    """
    Client for OpenAI-compatible inference endpoints.

    Works with Gemini, Llama, DeepSeek, and other compatible APIs.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        verify_ssl: bool = True,
        timeout: float = INFERENCE_API_TIMEOUT,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty

        http_client = self._create_http_client(verify_ssl, timeout)

        self.client = OpenAI(
            api_key=api_key,
            base_url=self.base_url,
            http_client=http_client,
        )

        logger.debug(
            "Initialized InferenceClient: url=%s, model=%s, verify_ssl=%s",
            self.base_url,
            model,
            verify_ssl,
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self.client.close()

    def __enter__(self) -> "InferenceClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - close the client."""
        self.close()

    def chat(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = INFERENCE_MAX_TOKENS,
        temperature: float = INFERENCE_TEMPERATURE,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> ChatCompletionMessage:
        """Send a chat completion request."""
        api_params = self._build_chat_params(
            messages, max_tokens, temperature, tools=tools, **kwargs
        )

        try:
            logger.debug("Calling inference API: model=%s", self.model)
            response = self.client.chat.completions.create(**api_params)

            if response.usage:
                logger.info(
                    "Token usage - prompt: %d, completion: %d, total: %d",
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                    response.usage.total_tokens,
                )

            return response.choices[0].message

        except APITimeoutError as e:
            logger.error("Request timed out after %s seconds", self.timeout)
            raise InferenceAPIError(
                f"Request timed out after {self.timeout} seconds"
            ) from e

        except APIConnectionError as e:
            logger.error("Connection error to inference API: %s", e)
            raise InferenceAPIError("Connection error to inference API") from e

        except Exception as e:
            logger.error(
                "Error calling inference API: %s - %s",
                type(e).__name__,
                str(e),
            )
            raise InferenceAPIError(
                f"Inference API error ({type(e).__name__}): {e}"
            ) from e

    async def chat_with_tools_async(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        execute_tool_func: Callable[[str, Dict[str, Any]], Awaitable[str]],
        max_iterations: int = INFERENCE_MAX_TOOL_ITERATIONS,
        max_tokens: int = INFERENCE_MAX_TOKENS,
        temperature: float = INFERENCE_TEMPERATURE,
    ) -> str:
        """
        Execute an agentic loop with tool calling.

        Iteratively calls the LLM and executes requested tools until a final
        answer is produced or max_iterations is reached.
        """
        messages = list(messages)
        logger.debug("Starting agentic loop with %d messages", len(messages))

        for iteration in range(1, max_iterations + 1):
            logger.debug("Agentic iteration %d/%d", iteration, max_iterations)

            loop = asyncio.get_running_loop()
            message = await loop.run_in_executor(
                None,
                functools.partial(
                    self.chat,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    tools=tools,
                ),
            )

            if not message.tool_calls:
                content = message.content or ""
                logger.info("Analysis complete after %d iteration(s)", iteration)
                logger.debug("Response preview: %s...", content[:200])
                return content

            logger.info(
                "Calling %d tool(s): %s",
                len(message.tool_calls),
                ", ".join(tc.function.name for tc in message.tool_calls),
            )
            messages.append(self._assistant_tool_message(message, message.tool_calls))

            for tc in message.tool_calls:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.function.name,
                        "content": await self._run_tool_call(tc, execute_tool_func),
                    }
                )

        logger.warning(
            "Reached maximum iterations (%d) without final answer", max_iterations
        )
        raise InferenceIterationLimitError(
            f"Maximum tool calling iterations ({max_iterations}) reached. "
            "Please try again with a simpler query."
        )

    def _create_http_client(self, verify_ssl: bool, timeout: float) -> httpx.Client:
        if not verify_ssl:
            logger.warning("SSL verification disabled for %s", self.base_url)
            return httpx.Client(verify=False, timeout=timeout)
        return httpx.Client(timeout=timeout)

    def _build_chat_params(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int,
        temperature: float,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }
        if self.top_p is not None:
            params["top_p"] = self.top_p
        if self.frequency_penalty is not None:
            params["frequency_penalty"] = self.frequency_penalty
        if tools:
            params["tools"] = tools
        return params

    @staticmethod
    def _assistant_tool_message(message: Any, tool_calls: List[Any]) -> Dict[str, Any]:
        return {
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in tool_calls
            ],
        }

    @staticmethod
    async def _run_tool_call(
        tool_call: Any,
        execute_tool_func: Callable[[str, Dict[str, Any]], Awaitable[str]],
    ) -> str:
        name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error("Failed to parse tool arguments: %s", e)
            return f"Error: Invalid JSON arguments - {e}"
        return await execute_tool_func(name, args)


async def _execute_tool_call(
    tool_name: str, tool_args: Dict[str, Any], tools_by_name: Dict[str, Any]
) -> str:
    """Execute a LangChain tool by name with the given arguments."""
    tool = tools_by_name.get(tool_name)
    if not tool:
        error_msg = f"Tool '{tool_name}' not found in available tools"
        logger.error(error_msg)
        return f"Error: {error_msg}"

    try:
        logger.info("Executing tool: %s", tool_name)
        try:
            logger.debug("Tool arguments: %s", json.dumps(tool_args))
        except (TypeError, ValueError):
            logger.debug("Tool arguments: %s", tool_args)
        result_str = str(await tool.ainvoke(tool_args))
        stripped = result_str.strip()

        if not stripped or stripped in {"null", "None", "{}", "[]"}:
            logger.warning("Tool %s returned empty or null result", tool_name)
        else:
            logger.info("Tool %s completed (%d chars)", tool_name, len(result_str))
            logger.debug("Tool result: %s", result_str)
        return result_str
    except Exception as e:
        error_msg = f"Error executing tool '{tool_name}': {e}"
        logger.error("%s", error_msg, exc_info=True)
        return f"Error: {error_msg}"


async def analyze_with_agentic(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Any]] = None,
    max_iterations: int = INFERENCE_MAX_TOOL_ITERATIONS,
) -> str:
    """
    Perform LLM analysis with optional tool calling.

    Uses the global inference client. If tools are provided, executes an
    agentic loop where the LLM can call tools iteratively.
    """
    try:
        client = get_inference_client()

        if not tools:
            logger.debug("No tools provided, doing simple chat completion")
            return client.chat(messages=messages).content or ""

        tools_by_name = {tool.name: tool for tool in tools}
        openai_tools = [convert_to_openai_tool(tool) for tool in tools]
        logger.info(
            "Starting agentic analysis with %d tools: %s",
            len(openai_tools),
            ", ".join(t["function"]["name"] for t in openai_tools),
        )

        async def execute_tool(tool_name, tool_args):
            return await _execute_tool_call(tool_name, tool_args, tools_by_name)

        return await client.chat_with_tools_async(
            messages=messages,
            tools=openai_tools,
            execute_tool_func=execute_tool,
            max_iterations=max_iterations,
        )
    except (InferenceAPIError, InferenceIterationLimitError):
        raise
    except Exception as e:
        logger.error("Error in agentic analysis: %s", e, exc_info=True)
        raise InferenceAPIError(f"Error in agentic analysis: {e}") from e


@functools.lru_cache(maxsize=1)
def get_inference_client() -> InferenceClient:
    """
    Get the global inference client instance (cached).

    Loads configuration from environment variables on first call.
    To reset: get_inference_client.cache_clear()
    """
    config = get_inference_config()

    logger.info(
        "Initializing global inference client: url=%s, model=%s",
        config["url"],
        config["model"],
    )

    return InferenceClient(
        base_url=config["url"],
        api_key=config["token"],
        model=config["model"],
        verify_ssl=config["verify_ssl"],
        timeout=config["timeout"],
        top_p=config["top_p"],
        frequency_penalty=config["frequency_penalty"],
    )


def get_inference_config() -> Dict[str, Any]:
    """Load inference configuration from environment variables."""
    required = ("INFERENCE_URL", "INFERENCE_TOKEN", "INFERENCE_MODEL")
    if missing := [name for name in required if not os.getenv(name)]:
        raise ValueError(
            f"Required environment variable(s) not set: {', '.join(missing)}"
        )

    url, token, model = (os.environ[name] for name in required)

    return {
        "url": url,
        "token": token,
        "model": model,
        "verify_ssl": os.getenv("INFERENCE_VERIFY_SSL", "true").lower() == "true",
        "timeout": float(
            os.getenv("INFERENCE_API_TIMEOUT", str(INFERENCE_API_TIMEOUT))
        ),
        "top_p": float(v) if (v := os.getenv("INFERENCE_TOP_P")) else None,
        "frequency_penalty": float(v)
        if (v := os.getenv("INFERENCE_FREQUENCY_PENALTY"))
        else None,
    }
