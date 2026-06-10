import os
import unittest
from unittest.mock import Mock, patch

from commons.inference import (
    InferenceClient,
    get_inference_client,
    get_inference_config,
    InferenceAPIError,
    InferenceIterationLimitError,
)


class TestInferenceConfig(unittest.TestCase):
    """Test configuration loading from environment variables."""

    def setUp(self):
        get_inference_client.cache_clear()

    @patch.dict(
        os.environ,
        {
            "INFERENCE_URL": "https://api.example.com",
            "INFERENCE_TOKEN": "test-token",
            "INFERENCE_MODEL": "test-model",
        },
        clear=True,
    )
    def test_get_inference_config_minimal(self):
        """Load config with only required env vars."""
        config = get_inference_config()
        self.assertEqual(config["url"], "https://api.example.com")
        self.assertEqual(config["token"], "test-token")
        self.assertEqual(config["model"], "test-model")
        self.assertTrue(config["verify_ssl"])
        self.assertEqual(config["timeout"], 120)

    @patch.dict(
        os.environ,
        {
            "INFERENCE_URL": "https://api.example.com",
            "INFERENCE_TOKEN": "test-token",
            "INFERENCE_MODEL": "test-model",
            "INFERENCE_VERIFY_SSL": "false",
            "INFERENCE_API_TIMEOUT": "60",
            "INFERENCE_TOP_P": "0.9",
            "INFERENCE_FREQUENCY_PENALTY": "0.5",
        },
        clear=True,
    )
    def test_get_inference_config_full(self):
        """Load config with all optional env vars set."""
        config = get_inference_config()
        self.assertFalse(config["verify_ssl"])
        self.assertEqual(config["timeout"], 60.0)
        self.assertEqual(config["top_p"], 0.9)
        self.assertEqual(config["frequency_penalty"], 0.5)

    @patch.dict(os.environ, {}, clear=True)
    def test_get_inference_config_missing_url(self):
        """Raise ValueError when required env var is missing."""
        with self.assertRaises(ValueError) as context:
            get_inference_config()
        self.assertIn("INFERENCE_URL", str(context.exception))

    @patch.dict(
        os.environ,
        {"INFERENCE_URL": "https://api.example.com"},
        clear=True,
    )
    def test_get_inference_config_missing_multiple(self):
        """Report all missing required env vars in error."""
        with self.assertRaises(ValueError) as context:
            get_inference_config()
        error_msg = str(context.exception)
        self.assertIn("INFERENCE_TOKEN", error_msg)
        self.assertIn("INFERENCE_MODEL", error_msg)


class TestInferenceClient(unittest.TestCase):
    """Test InferenceClient initialization and core methods."""

    @patch("commons.inference.client.OpenAI")
    def test_init_with_defaults(self, mock_openai):
        """Initialize client with default parameters."""
        client = InferenceClient(
            base_url="https://api.example.com",
            api_key="test-key",
            model="test-model",
        )

        self.assertEqual(client.model, "test-model")
        self.assertEqual(client.timeout, 120)
        self.assertEqual(client.base_url, "https://api.example.com")
        mock_openai.assert_called_once()

    @patch("commons.inference.client.OpenAI")
    def test_init_strips_trailing_slash(self, mock_openai):
        """Strip trailing slash from base_url."""
        client = InferenceClient(
            base_url="https://api.example.com/",
            api_key="test-key",
            model="test-model",
        )

        self.assertEqual(client.base_url, "https://api.example.com")

    @patch("commons.inference.client.OpenAI")
    def test_context_manager(self, mock_openai):
        """Client can be used as context manager and closes properly."""
        mock_client = Mock()
        mock_openai.return_value = mock_client

        with InferenceClient(
            base_url="https://api.example.com",
            api_key="test-key",
            model="test-model",
        ) as client:
            self.assertEqual(client.model, "test-model")

        mock_client.close.assert_called_once()

    @patch("commons.inference.client.OpenAI")
    def test_chat_success(self, mock_openai):
        """Send successful chat request and return message."""
        mock_message = Mock()
        mock_message.content = "Hello, world!"
        mock_message.tool_calls = None

        mock_response = Mock()
        mock_response.choices = [Mock(message=mock_message)]
        mock_response.usage = Mock(
            prompt_tokens=10, completion_tokens=5, total_tokens=15
        )

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        client = InferenceClient(
            base_url="https://api.example.com",
            api_key="test-key",
            model="test-model",
        )

        messages = [{"role": "user", "content": "Hello"}]
        response = client.chat(messages)

        self.assertEqual(response.content, "Hello, world!")
        mock_client.chat.completions.create.assert_called_once()

    @patch("commons.inference.client.OpenAI")
    def test_chat_with_tools(self, mock_openai):
        """Include tools in chat request params."""
        mock_message = Mock()
        mock_message.content = "Response"
        mock_message.tool_calls = None

        mock_response = Mock()
        mock_response.choices = [Mock(message=mock_message)]
        mock_response.usage = None

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        client = InferenceClient(
            base_url="https://api.example.com",
            api_key="test-key",
            model="test-model",
        )

        tools = [{"type": "function", "function": {"name": "test_tool"}}]
        messages = [{"role": "user", "content": "Test"}]
        response = client.chat(messages, tools=tools)

        call_args = mock_client.chat.completions.create.call_args
        self.assertIn("tools", call_args.kwargs)

    @patch("commons.inference.client.OpenAI")
    def test_chat_timeout_error(self, mock_openai):
        """Raise InferenceAPIError on request timeout."""
        from openai import APITimeoutError

        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = APITimeoutError(
            request=Mock()
        )
        mock_openai.return_value = mock_client

        client = InferenceClient(
            base_url="https://api.example.com",
            api_key="test-key",
            model="test-model",
        )

        messages = [{"role": "user", "content": "Hello"}]

        with self.assertRaises(InferenceAPIError) as context:
            client.chat(messages)
        self.assertIn("timed out", str(context.exception))

    @patch("commons.inference.client.OpenAI")
    def test_chat_connect_error(self, mock_openai):
        """Raise InferenceAPIError on connection failure."""
        from openai import APIConnectionError

        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = APIConnectionError(
            request=Mock()
        )
        mock_openai.return_value = mock_client

        client = InferenceClient(
            base_url="https://api.example.com",
            api_key="test-key",
            model="test-model",
        )

        messages = [{"role": "user", "content": "Hello"}]

        with self.assertRaises(InferenceAPIError) as context:
            client.chat(messages)
        self.assertIn("Connection error", str(context.exception))

    @patch("commons.inference.client.OpenAI")
    def test_chat_generic_error(self, mock_openai):
        """Wrap generic exceptions in InferenceAPIError."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client

        client = InferenceClient(
            base_url="https://api.example.com",
            api_key="test-key",
            model="test-model",
        )

        messages = [{"role": "user", "content": "Hello"}]

        with self.assertRaises(InferenceAPIError):
            client.chat(messages)


class TestGlobalClient(unittest.TestCase):
    """Test global singleton client factory."""

    def setUp(self):
        get_inference_client.cache_clear()

    @patch.dict(
        os.environ,
        {
            "INFERENCE_URL": "https://api.example.com",
            "INFERENCE_TOKEN": "test-token",
            "INFERENCE_MODEL": "test-model",
        },
        clear=True,
    )
    @patch("commons.inference.client.InferenceClient")
    def test_get_inference_client_singleton(self, mock_client_class):
        """Return cached client on subsequent calls."""
        client1 = get_inference_client()
        client2 = get_inference_client()

        self.assertEqual(mock_client_class.call_count, 1)
        self.assertIs(client1, client2)

    @patch.dict(
        os.environ,
        {
            "INFERENCE_URL": "https://api.example.com",
            "INFERENCE_TOKEN": "test-token",
            "INFERENCE_MODEL": "test-model",
        },
        clear=True,
    )
    @patch("commons.inference.client.InferenceClient")
    def test_cache_clear(self, mock_client_class):
        """Create new client after cache_clear."""
        client1 = get_inference_client()
        get_inference_client.cache_clear()
        client2 = get_inference_client()

        self.assertEqual(mock_client_class.call_count, 2)


class TestChatWithToolsAsync(unittest.IsolatedAsyncioTestCase):
    """Test agentic loop with tool calling."""

    @patch("commons.inference.client.OpenAI")
    async def test_messages_not_mutated(self, mock_openai):
        """Original messages list is not mutated by chat_with_tools_async."""
        mock_message = Mock()
        mock_message.content = "Final answer"
        mock_message.tool_calls = None

        mock_response = Mock()
        mock_response.choices = [Mock(message=mock_message)]
        mock_response.usage = None

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        client = InferenceClient(
            base_url="https://api.example.com",
            api_key="test-key",
            model="test-model",
        )

        original_messages = [{"role": "user", "content": "Test"}]
        original_length = len(original_messages)

        await client.chat_with_tools_async(
            messages=original_messages,
            tools=[],
            execute_tool_func=Mock(),
        )

        self.assertEqual(len(original_messages), original_length)

    @patch("commons.inference.client.OpenAI")
    async def test_chat_with_tools_no_tool_calls(self, mock_openai):
        """Return final answer when LLM makes no tool calls."""
        mock_message = Mock()
        mock_message.content = "Final answer"
        mock_message.tool_calls = None

        mock_response = Mock()
        mock_response.choices = [Mock(message=mock_message)]
        mock_response.usage = None

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        client = InferenceClient(
            base_url="https://api.example.com",
            api_key="test-key",
            model="test-model",
        )

        async def mock_executor(name, args):
            return "tool result"

        messages = [{"role": "user", "content": "Test"}]
        result = await client.chat_with_tools_async(
            messages=messages, tools=[], execute_tool_func=mock_executor
        )

        self.assertEqual(result, "Final answer")

    @patch("commons.inference.client.OpenAI")
    async def test_chat_with_tools_max_iterations(self, mock_openai):
        """Raise InferenceIterationLimitError when max iterations reached."""
        mock_tool_call = Mock()
        mock_tool_call.id = "call_1"
        mock_tool_call.function.name = "test_tool"
        mock_tool_call.function.arguments = '{"arg": "value"}'

        mock_message = Mock()
        mock_message.content = ""
        mock_message.tool_calls = [mock_tool_call]

        mock_response = Mock()
        mock_response.choices = [Mock(message=mock_message)]
        mock_response.usage = None

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        client = InferenceClient(
            base_url="https://api.example.com",
            api_key="test-key",
            model="test-model",
        )

        async def mock_executor(name, args):
            return "tool result"

        messages = [{"role": "user", "content": "Test"}]

        with self.assertRaises(InferenceIterationLimitError):
            await client.chat_with_tools_async(
                messages=messages,
                tools=[],
                execute_tool_func=mock_executor,
                max_iterations=2,
            )


if __name__ == "__main__":
    unittest.main()
