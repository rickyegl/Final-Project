from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Dict, Optional

try:  # Windows standard library support
    import winsound  # type: ignore
except ImportError:  # pragma: no cover - non-Windows fallback
    winsound = None  # type: ignore


SOUND_FILES: Dict[str, str] = {
    "app_start": "app_start.wav",
    "window_close": "window_close.wav",
    "great_job": "great_job.wav",
    "wrong": "wrong.wav",
    "mad_sounds": "mad_sounds.wav",
}

FUNCTION_SOUND_MAP: Dict[str, str] = {
    "play_great_job_sound": "great_job",
    "play_wrong_sound": "wrong",
    "play_mad_sounds": "mad_sounds",
}


class AudioManager:
    """Centralised helper for playing Baldi sound effects."""

    def __init__(self, assets_dir: Path, character_audio_subdir: str = "") -> None:
        self._assets_dir = assets_dir
        self._character_audio_subdir = character_audio_subdir
        self._lock = threading.Lock()

    def play_event(self, sound_key: str, *, blocking: bool = False) -> dict[str, str]:
        """Play a named sound event and return metadata for logging/tool feedback."""
        filename = SOUND_FILES.get(sound_key)
        if filename is None:
            return {
                "status": "error",
                "reason": f"Unknown sound key '{sound_key}'",
            }
        return self._play_file(filename, blocking=blocking)

    def handle_function_call(self, function_name: str) -> dict[str, str]:
        """Play the audio mapped from a Gemini function call."""
        sound_key = FUNCTION_SOUND_MAP.get(function_name)
        if sound_key is None:
            return {
                "status": "error",
                "reason": f"Unsupported function '{function_name}'",
            }
        return self.play_event(sound_key)

    def _play_file(self, filename: str, *, blocking: bool) -> dict[str, str]:
        # Try character-specific audio first, fall back to root assets
        if self._character_audio_subdir:
            char_path = self._assets_dir / self._character_audio_subdir / filename
            if char_path.exists():
                path = char_path
            else:
                path = self._assets_dir / filename
        else:
            path = self._assets_dir / filename

        if not path.exists():
            return {
                "status": "error",
                "reason": f"Missing audio asset '{filename}'",
            }

        with self._lock:
            if winsound:  # Windows playback (async when requested)
                flags = winsound.SND_FILENAME
                if not blocking:
                    flags |= winsound.SND_ASYNC
                winsound.PlaySound(str(path), flags)
                return {
                    "status": "played",
                    "file": filename,
                    "platform": sys.platform,
                    "blocking": "yes" if blocking else "no",
                }
            return {
                "status": "unsupported",
                "file": filename,
                "platform": sys.platform,
                "blocking": "yes" if blocking else "no",
            }


_AUDIO_MANAGER: Optional[AudioManager] = None


def get_audio_manager() -> AudioManager:
    """Return a process-wide audio manager, initialising it on first use."""
    global _AUDIO_MANAGER
    if _AUDIO_MANAGER is None:
        assets_root = Path(__file__).resolve().parents[2] / "assets"
        _AUDIO_MANAGER = AudioManager(assets_root)
    return _AUDIO_MANAGER


__all__ = [
    "AudioManager",
    "FUNCTION_SOUND_MAP",
    "SOUND_FILES",
    "get_audio_manager",
]
