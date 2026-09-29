"""Remote open-model provider abstraction for external LLM/SLM APIs.

Supports online hosted providers speaking OpenAI-compatible chat completions APIs,
including Hugging Face Inference Providers, OpenRouter, Groq, Together AI, etc.

Key design principles:
1. Provider-agnostic abstraction implementing the GenerationProvider protocol.
2. Robust error handling for remote hosted environments (timeouts, 401/403 auth, 429 rate limits, 5xx outages).
3. Resilient model availability check (avoids crashing if hosted provider limits or omits GET /models).
4. No credential leaks: API keys and connection secrets are sanitized from logs and exception messages.
"""

import logging
import re
import time
from urllib.parse import urlsplit

import httpx

from app.generation.base import GenerationError, GenerationRequest, GenerationResult
from app.generation.openai_compatible import _THINKING, display_url, is_local

logger = logging.getLogger(__name__)

# Known public provider endpoints default mappings
PROVIDER_BASE_URLS = {
    "huggingface": "https://router.huggingface.co/hf-inference/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "openai_compatible": "http://127.0.0.1:11434/v1",
}


class RemoteOpenModelProvider:
    name = "remote_open_model"

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 120.0,
        provider_name: str = "remote_open_model",
        transport: httpx.BaseTransport | None = None,
    ):
        self.provider_name = provider_name
        self.name = provider_name
        self.model = model
        self.where = display_url(base_url)
        
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        if "openrouter.ai" in base_url:
            headers["HTTP-Referer"] = "https://github.com/campusmate"
            headers["X-Title"] = "CampusMate AI"

        self._client = httpx.Client(
            base_url=base_url.rstrip("/") + "/",
            headers=headers,
            timeout=timeout,
            transport=transport,
        )

    def _call(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise GenerationError(
                f"Remote provider ({self.provider_name} @ {self.where}) timed out after {self._client.timeout.read}s"
            ) from exc
        except httpx.HTTPError as exc:
            raise GenerationError(
                f"Cannot connect to remote provider ({self.provider_name} @ {self.where}): {type(exc).__name__}"
            ) from exc

        if response.status_code == 401 or response.status_code == 403:
            raise GenerationError(
                f"Authentication failed for remote provider ({self.provider_name}): HTTP {response.status_code}. "
                "Check your API key configuration."
            )
        elif response.status_code == 429:
            raise GenerationError(
                f"Rate limit exceeded on remote provider ({self.provider_name}): HTTP 429."
            )
        elif response.status_code >= 400:
            raise GenerationError(
                f"Remote provider ({self.provider_name} @ {self.where}) returned HTTP {response.status_code}: "
                f"{response.text[:200]}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise GenerationError(
                f"Remote provider ({self.provider_name} @ {self.where}) returned non-JSON response"
            ) from exc

    def check(self) -> str:
        """Verify remote connectivity.
        
        Tries GET models if available; if not supported or restricted (HTTP 404/403),
        falls back gracefully without raising an error.
        """
        try:
            res = self._client.get("models")
            if res.status_code == 200:
                data = res.json().get("data", [])
                available = [m.get("id") for m in data if isinstance(m, dict)]
                if available and self.model not in available:
                    logger.warning(
                        "Configured model %r not listed in provider model list (available: %s)",
                        self.model,
                        ", ".join(map(str, available[:5])),
                    )
        except Exception as exc:
            logger.debug("Models endpoint check skipped for %s: %s", self.where, exc)

        return f"{self.provider_name}: {self.model} at {self.where}"

    def generate(self, request: GenerationRequest) -> GenerationResult:
        from app.generation.prompt import render_messages

        started = time.perf_counter()
        messages = render_messages(request)

        body = self._call(
            "POST",
            "chat/completions",
            json={
                "model": self.model,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": False,
            },
        )

        try:
            text = body["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise GenerationError(
                f"Unexpected response payload from remote provider ({self.provider_name}): missing choices[0].message.content"
            ) from exc

        usage = body.get("usage") or {}
        cleaned_text = _THINKING.sub("", text).strip()
        elapsed_ms = round((time.perf_counter() - started) * 1000)

        return GenerationResult(
            text=cleaned_text,
            provider=self.provider_name,
            model=self.model,
            latency_ms=elapsed_ms,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )
