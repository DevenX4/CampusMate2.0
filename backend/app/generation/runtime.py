"""The configured generation provider, one per process. The only place that knows which
provider classes exist; everything else asks for a GenerationProvider."""

import logging
from functools import lru_cache

from app.core.config import get_settings
from app.generation.base import GenerationProvider
from app.generation.extractive import ExtractiveProvider
from app.generation.openai_compatible import OpenAICompatibleProvider, display_url, is_local

logger = logging.getLogger(__name__)


@lru_cache
def get_generator() -> GenerationProvider:
    settings = get_settings()
    if settings.generation_provider == "openai_compatible":
        if not is_local(settings.generation_base_url):
            logger.warning("Generation server %s is not on this machine: questions and evidence are sent to it",
                           display_url(settings.generation_base_url))
        api_key = settings.generation_api_key.get_secret_value() if settings.generation_api_key else None
        return OpenAICompatibleProvider(settings.generation_base_url, settings.generation_model, api_key,
                                        settings.generation_timeout_seconds)
    return ExtractiveProvider()
