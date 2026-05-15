"""
Custom dynamic model factory for MiniMax API.

Load this module with:

    $env:AGNOCLAW_MODEL_FACTORY_MODULES="custom_models.minimax"

Required environment variables:

    MINIMAX_API_KEY
"""

from __future__ import annotations

import os

from agno.models.anthropic import Claude
from agnoclaw.model_factory import ModelSpec, register_model_factory


@register_model_factory("minimax")
def create_minimax_model(spec: ModelSpec):
    """Create Anthropic model for MiniMax API."""

    api_key = (
        os.getenv("MINIMAX_API_KEY")
        or spec.options.get("api_key")
    )

    if not api_key:
        raise ValueError(
            "MINIMAX_API_KEY is required for provider 'minimax'."
        )

    return Claude(
        id=spec.model,
        api_key=api_key,
        client_params={
            "base_url": "https://api.minimaxi.com/anthropic",
        },
    )