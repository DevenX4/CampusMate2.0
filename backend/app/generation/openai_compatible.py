"""Any server that speaks the OpenAI chat-completions API: Ollama, llama.cpp's llama-server,
LM Studio and vLLM on this machine, or a hosted API. One class and no model-specific code:
the model is only a name sent with each request.

    POST {base_url}/chat/completions   {"model", "messages", "temperature", "max_tokens", "stream": false}
    GET  {base_url}/models             (check: is the configured model there?)

The model runs in its own process, not inside the API: a crash or an out-of-memory error in
the model server cannot take CampusMate down, and models are swapped without reinstalling.
"""

import re
import time
from urllib.parse import urlsplit

import httpx

from app.generation.base import GenerationError, GenerationRequest, GenerationResult
from app.generation.prompt import render_messages

# Reasoning models may start with a <think>...</think> block; only the answer after it is kept.
_THINKING = re.compile(r"^\s*<think>.*?</think>\s*", re.S)


def is_local(url: str) -> bool:
    return urlsplit(url).hostname in ("localhost", "127.0.0.1", "::1")


def display_url(url: str) -> str:
    """The URL without any user:password@ part, safe for messages and logs."""
    parts = urlsplit(url)
    return parts._replace(netloc=parts.netloc.rsplit("@", 1)[-1]).geturl()


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def __init__(self, base_url: str, model: str, api_key: str | None = None, timeout: float = 120.0,
                 transport: httpx.BaseTransport | None = None):
        self.model = model
        self.where = display_url(base_url)
        # The key goes in a header of requests to base_url only, and never into messages or logs.
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.Client(base_url=base_url.rstrip("/") + "/", headers=headers, timeout=timeout,
                                    transport=transport)

    def _call(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise GenerationError(f"{self.where} did not answer within the timeout") from exc
        except httpx.HTTPError as exc:
            raise GenerationError(f"cannot reach {self.where} ({type(exc).__name__}); is the model server running?") from exc
        if response.status_code >= 400:
            raise GenerationError(f"{method} {path} at {self.where} returned HTTP {response.status_code}: "
                                  f"{response.text[:200]}")
        try:
            return response.json()
        except ValueError as exc:
            raise GenerationError(f"{path} at {self.where} did not return JSON") from exc

    def check(self) -> str:
        available = [m.get("id") for m in self._call("GET", "models").get("data", [])]
        if self.model not in available:
            raise GenerationError(f"model {self.model!r} is not available at {self.where}; "
                                  f"the server has: {', '.join(map(str, available)) or 'no models'}")
        return f"{self.name}: {self.model} at {self.where}"

    def generate(self, request: GenerationRequest) -> GenerationResult:
        started = time.perf_counter()
        body = self._call("POST", "chat/completions", json={
            "model": self.model, "messages": render_messages(request), "temperature": request.temperature,
            "max_tokens": request.max_tokens, "stream": False})
        try:
            text = body["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise GenerationError(f"unexpected response from {self.where}: no choices[0].message.content") from exc
        usage = body.get("usage") or {}
        return GenerationResult(_THINKING.sub("", text).strip(), self.name, self.model,
                                round((time.perf_counter() - started) * 1000),
                                usage.get("prompt_tokens"), usage.get("completion_tokens"))
