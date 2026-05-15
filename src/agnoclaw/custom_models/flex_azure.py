"""
Custom dynamic model factory for Flex internal Azure OpenAI APIM gateway.

Load this module with:

    $env:AGNOCLAW_MODEL_FACTORY_MODULES="custom_models.flex_azure"

Required environment variables:

    FLEX_AZURE_OPENAI_API_KEY
    FLEX_AZURE_OPENAI_BASE_URL

Optional:

    FLEX_AZURE_OPENAI_API_VERSION
"""

from __future__ import annotations

import os

from agno.models.openai import OpenAILike
from agnoclaw.model_factory import ModelSpec, register_model_factory


@register_model_factory("flex-azure-openai")
def create_flex_azure_openai_model(spec: ModelSpec):
    """Create OpenAILike model for Flex Azure OpenAI APIM gateway."""

    base_url = (
        os.getenv("FLEX_AZURE_OPENAI_BASE_URL")
        or spec.options.get("base_url")
    )

    api_key = (
        os.getenv("FLEX_AZURE_OPENAI_API_KEY")
        or spec.options.get("api_key")
    )

    api_version = (
        os.getenv("FLEX_AZURE_OPENAI_API_VERSION")
        or spec.options.get("api_version")
        or "2025-03-01-preview"
    )

    if not base_url:
        raise ValueError(
            "FLEX_AZURE_OPENAI_BASE_URL is required for provider "
            "'flex-azure-openai'."
        )

    if not api_key:
        raise ValueError(
            "FLEX_AZURE_OPENAI_API_KEY is required for provider "
            "'flex-azure-openai'."
        )

    return OpenAILike(
        id=spec.model,
        base_url=base_url,
        client_params={
            "default_headers": {
                "api-key": api_key,
            },
            "default_query": {
                "api-version": api_version,
            },
        },
    )
