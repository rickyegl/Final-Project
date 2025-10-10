from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


DEFAULT_MODEL = "gemini-flash-latest"
DEFAULT_HISTORY_LIMIT = 10
_ENV_LOADED = False


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration for the Baldi teacher chatbot."""

    api_key: str
    model: str = DEFAULT_MODEL
    max_turn_history: int = DEFAULT_HISTORY_LIMIT
    temperature: float = 0.8
    top_p: float = 0.95
    top_k: int = 40

    @classmethod
    def from_env(
        cls, *, prefix: str = "BALDI_", api_key: Optional[str] = None
    ) -> "AppConfig":
        """Create configuration from environment variables."""
        _ensure_env_loaded()
        api_key = (
            api_key
            or os.getenv(f"{prefix}GEMINI_API_KEY")
            or os.getenv("GEMINI_API_KEY")
        )
        if not api_key:
            raise RuntimeError(
                "Missing Gemini API key. Set BALDI_GEMINI_API_KEY or GEMINI_API_KEY."
            )

        model = os.getenv(f"{prefix}MODEL") or DEFAULT_MODEL
        max_turn_history = _get_int_env(f"{prefix}MAX_TURN_HISTORY", DEFAULT_HISTORY_LIMIT)
        temperature = _get_float_env(f"{prefix}TEMPERATURE", 0.8)
        top_p = _get_float_env(f"{prefix}TOP_P", 0.95)
        top_k = _get_int_env(f"{prefix}TOP_K", 40)

        return cls(
            api_key=api_key,
            model=model,
            max_turn_history=max_turn_history,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
        )


def _get_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer.") from exc


def _get_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be a float.") from exc


def _ensure_env_loaded() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return

    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue
            key, value = map(str.strip, stripped.split("=", 1))
            os.environ.setdefault(key, value)
    _ENV_LOADED = True
