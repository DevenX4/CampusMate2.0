"""The configured generation provider, one per process. The only place that knows which
provider classes exist; everything else asks for a GenerationProvider."""

import logging
from functools import lru_cache

from app.core.config import get_settings
from app.generation.base import GenerationProvider
from app.generation.extractive import ExtractiveProvider
from app.generation.openai_compatible import OpenAICompatibleProvider, display_url, is_local
from app.generation.remote_open_model import PROVIDER_BASE_URLS, RemoteOpenModelProvider

logger = logging.getLogger(__name__)


@lru_cache
def get_generator() -> GenerationProvider:
    settings = get_settings()
    provider = settings.generation_provider

    if provider in ("remote_open_model", "huggingface", "openrouter"):
        base_url = settings.generation_base_url
        # If user selected a specific provider name but left the default local base_url, set appropriate default URL
        if base_url == "http://127.0.0.1:11434/v1" and provider in PROVIDER_BASE_URLS:
            base_url = PROVIDER_BASE_URLS[provider]

        if not is_local(base_url):
            logger.info("Using remote open model provider (%s @ %s)", provider, display_url(base_url))

        api_key = settings.generation_api_key.get_secret_value() if settings.generation_api_key else None
        return RemoteOpenModelProvider(
            base_url=base_url,
            model=settings.generation_model,
            api_key=api_key,
            timeout=settings.generation_timeout_seconds,
            provider_name=provider,
        )

    if provider == "openai_compatible":
        if not is_local(settings.generation_base_url):
            logger.warning("Generation server %s is not on this machine: questions and evidence are sent to it",
                           display_url(settings.generation_base_url))
        api_key = settings.generation_api_key.get_secret_value() if settings.generation_api_key else None
        return OpenAICompatibleProvider(settings.generation_base_url, settings.generation_model, api_key,
                                        settings.generation_timeout_seconds)

    return ExtractiveProvider()

