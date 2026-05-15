# Import all custom models to trigger @register_model_factory decorators
try:
    from . import flex_azure, minimax
except ImportError:
    # openai not installed; flex_azure unavailable
    pass