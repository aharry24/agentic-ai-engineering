"""Settings read from environment variables (or a local .env file)."""
import os
from dataclasses import dataclass

try:                                    # optional: load a .env file when python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DEFAULT_MODELS = {"openai": "gpt-5-mini", "anthropic": "claude-sonnet-4-5"}
KEY_NAMES = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}

# CrewAI: no telemetry, and no interactive "view your traces?" prompt that blocks a run
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")


@dataclass(frozen=True)
class Settings:
    provider: str
    model: str


def get_settings() -> Settings:
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    if provider not in DEFAULT_MODELS:
        raise ValueError('LLM_PROVIDER must be "openai" or "anthropic"')
    return Settings(provider=provider, model=os.environ.get("LLM_MODEL", DEFAULT_MODELS[provider]))


def require_keys() -> None:
    """Fail early, with a clear message, if a key the live agents need is missing."""
    settings = get_settings()
    missing = [k for k in (KEY_NAMES[settings.provider], "TAVILY_API_KEY") if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}. "
                           "Set them in your shell or in a .env file (see .env.example).")
