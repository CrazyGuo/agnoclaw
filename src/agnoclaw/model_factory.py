"""
Dynamic model factory registry for agnoclaw.

This module allows agnoclaw users to dynamically register custom model
constructors without modifying agnoclaw's core AgentHarness logic.

Discovery methods:
1. AGNOCLAW_MODEL_FACTORY_MODULES="custom_models.flex_azure,custom_models.minimax"
2. Python entry points: group = "agnoclaw.model_factories"
"""

from __future__ import annotations

import importlib
import json
import logging
import os
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from typing import Any, Callable

logger = logging.getLogger("agnoclaw.model_factory")


@dataclass
class ModelSpec:
    """Input passed to every registered model factory."""

    model: str
    provider: str
    config: Any
    options: dict[str, Any] = field(default_factory=dict)


ModelFactory = Callable[[ModelSpec], Any | None]

_MODEL_FACTORIES: dict[str, ModelFactory] = {}
_DISCOVERED = False


def normalize_provider(provider: str) -> str:
    """Normalize provider names consistently."""
    return provider.strip().lower().replace("_", "-")


def register_model_factory(
    provider: str,
    factory: ModelFactory | None = None,
) -> Callable[[ModelFactory], ModelFactory] | ModelFactory:
    """
    Register a model factory for a provider.

    Decorator style:

        @register_model_factory("flex-azure-openai")
        def create_model(spec: ModelSpec):
            ...

    Function style:

        register_model_factory("flex-azure-openai", create_model)
    """

    normalized_provider = normalize_provider(provider)

    def decorator(func: ModelFactory) -> ModelFactory:
        _MODEL_FACTORIES[normalized_provider] = func
        logger.debug("Registered model factory for provider=%s", normalized_provider)
        return func

    if factory is not None:
        return decorator(factory)

    return decorator


def get_registered_model_factories() -> dict[str, ModelFactory]:
    """Return a copy of currently registered factories."""
    return dict(_MODEL_FACTORIES)


def discover_model_factories(force: bool = False) -> None:
    """
    Discover external model factories.

    Discovery sources:
    1. AGNOCLAW_MODEL_FACTORY_MODULES
    2. Python entry points group: agnoclaw.model_factories
    """

    global _DISCOVERED

    if _DISCOVERED and not force:
        return

    _load_modules_from_env()
    _load_entry_point_factories()

    _DISCOVERED = True


def resolve_custom_model(
    model: str,
    provider: str,
    config: Any,
) -> Any | None:
    """
    Resolve provider/model into a custom Agno Model object.

    Returns:
        Agno Model object if a registered factory handles this provider.
        None if no registered factory handles this provider.
    """

    discover_model_factories()

    normalized_provider = normalize_provider(provider)
    options = _load_model_options_from_env()

    spec = ModelSpec(
        model=model,
        provider=normalized_provider,
        config=config,
        options=options,
    )

    factory = _MODEL_FACTORIES.get(normalized_provider)

    if factory is None:
        return None

    logger.debug(
        "Resolving custom model with provider=%s model=%s",
        normalized_provider,
        model,
    )

    return factory(spec)


def _load_modules_from_env() -> None:
    modules_value = os.getenv("AGNOCLAW_MODEL_FACTORY_MODULES", "").strip()

    if not modules_value:
        return

    module_names = [
        item.strip()
        for item in modules_value.split(",")
        if item.strip()
    ]

    for module_name in module_names:
        try:
            importlib.import_module(module_name)
            logger.info("Loaded model factory module: %s", module_name)
        except Exception:
            logger.exception("Failed to load model factory module: %s", module_name)
            raise


def _load_entry_point_factories() -> None:
    """Load model factories from installed Python packages."""

    try:
        eps = entry_points()
        if hasattr(eps, "select"):
            selected = eps.select(group="agnoclaw.model_factories")
        else:
            selected = eps.get("agnoclaw.model_factories", [])
    except Exception:
        logger.exception("Failed to read agnoclaw.model_factories entry points")
        return

    for ep in selected:
        try:
            loaded = ep.load()

            if callable(loaded):
                value = loaded()
            else:
                value = loaded

            if value is None:
                continue

            if isinstance(value, dict):
                for provider, factory in value.items():
                    register_model_factory(provider, factory)
                continue

            logger.warning(
                "Ignored model factory entry point %s because it did not "
                "register factories or return dict[str, ModelFactory].",
                ep.name,
            )

        except Exception:
            logger.exception("Failed to load model factory entry point: %s", ep.name)
            raise


def _load_model_options_from_env() -> dict[str, Any]:
    """
    Optional generic JSON configuration.

    Example:
        AGNOCLAW_MODEL_CONFIG_JSON='{"base_url":"...","api_version":"..."}'
    """

    raw = os.getenv("AGNOCLAW_MODEL_CONFIG_JSON", "").strip()

    if not raw:
        return {}

    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("AGNOCLAW_MODEL_CONFIG_JSON is not valid JSON") from exc

    if not isinstance(value, dict):
        raise ValueError("AGNOCLAW_MODEL_CONFIG_JSON must be a JSON object")

    return value
