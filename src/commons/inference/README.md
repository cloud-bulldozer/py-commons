# commons.inference

LLM inference client for OpenAI-compatible APIs.

## Install

```bash
pip install py-commons
```

## Quick Start

```python
import os
from commons.inference import get_inference_client

os.environ["INFERENCE_URL"] = "https://api.openai.com/v1"
os.environ["INFERENCE_TOKEN"] = "your-api-key"
os.environ["INFERENCE_MODEL"] = "gpt-4"

client = get_inference_client()
message = client.chat([{"role": "user", "content": "Hello"}])
print(message.content)
```

## Environment Variables

**Required:**
- `INFERENCE_URL` - API endpoint URL
- `INFERENCE_TOKEN` - Authentication token
- `INFERENCE_MODEL` - Model name

**Optional:**
- `INFERENCE_VERIFY_SSL` - Verify SSL certs (default: `true`)
- `INFERENCE_API_TIMEOUT` - Request timeout in seconds (default: `120`)
- `INFERENCE_TOP_P` - Nucleus sampling probability
- `INFERENCE_FREQUENCY_PENALTY` - Token frequency penalty

## Tool Calling

```python
import asyncio
from commons.inference import analyze_with_agentic
from langchain_core.tools import StructuredTool

def get_weather(location: str) -> str:
    return f"Weather in {location}: sunny"

async def main():
    tool = StructuredTool.from_function(get_weather, name="get_weather")
    messages = [{"role": "user", "content": "What's the weather in Paris?"}]
    
    result = await analyze_with_agentic(messages, tools=[tool])
    print(result)

asyncio.run(main())
```

## Direct Client

```python
from commons.inference import InferenceClient

with InferenceClient(
    base_url="https://api.openai.com/v1",
    api_key="your-key",
    model="gpt-4",
    verify_ssl=True,
    timeout=120
) as client:
    response = client.chat([{"role": "user", "content": "Hello"}])
    print(response.content)
```

## API

### InferenceClient

Main client for OpenAI-compatible inference endpoints. Can be used as a context manager.

**Methods:**
- `chat(messages, max_tokens=8192, temperature=0.01, tools=None)` - Send chat request
- `chat_with_tools_async(messages, tools, execute_tool_func, max_iterations=5)` - Agentic loop
- `close()` - Close underlying HTTP client
- Context manager support - `with InferenceClient(...) as client:`

### Functions

- `get_inference_client()` - Get global singleton client (cached)
- `get_inference_config()` - Load config from environment variables
- `analyze_with_agentic(messages, tools=None, max_iterations=5)` - High-level agentic analysis

### Exceptions

- `InferenceClientError` - Base exception for all inference errors
- `InferenceAPIError` - API errors (timeout, connection, server errors)
- `InferenceIterationLimitError` - Max tool-calling iterations exceeded

## Resource Management

The `InferenceClient` manages an HTTP connection pool. For long-running applications, use it as a context manager or call `close()` explicitly:

```python
from commons.inference import InferenceClient

# Context manager (recommended)
with InferenceClient(...) as client:
    response = client.chat(messages)

# Manual cleanup
client = InferenceClient(...)
try:
    response = client.chat(messages)
finally:
    client.close()
```

The global singleton from `get_inference_client()` is automatically managed - no cleanup needed.

## Compatible APIs

Works with any OpenAI-compatible endpoint:
- OpenAI GPT
- Google Gemini
- Meta Llama
- DeepSeek
- Local servers (vLLM, Ollama, etc.)
