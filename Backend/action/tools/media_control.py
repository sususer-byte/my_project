#System volume and media playback control.

import logging
import platform
import subprocess
from typing import Any, Dict

from pydantic import BaseModel, Field

logger = logging.getLogger("furgal.action.tools")

_pyautogui_available = False

try:
    import pyautogui
    _pyautogui_available = True
except ImportError:
    logger.warning("pyautogui not installed; media key simulation unavailable")


class VolumeParams(BaseModel):
    direction: str = Field(description="Volume direction: 'up', 'down', or 'mute'")
    steps: int = Field(default=2, ge=1, le=20, description="Number of volume steps")


class MediaKeyParams(BaseModel):
    action: str = Field(description="Media action: 'play_pause', 'next', 'previous', 'stop'")


_MEDIA_KEY_MAP = {
    "play_pause": "playpause",
    "next": "nexttrack",
    "previous": "prevtrack",
    "stop": "stop",
}


def _adjust_volume_windows(direction: str, steps: int) -> Dict[str, Any]:
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        if direction == "mute":
            volume.SetMute(1, None)
            return {"success": True, "action": "mute"}
        current = volume.GetMasterVolumeLevelScalar()
        step = 0.05
        for _ in range(steps):
            if direction == "up":
                current = min(1.0, current + step)
            else:
                current = max(0.0, current - step)
        volume.SetMasterVolumeLevelScalar(current, None)
        return {"success": True, "action": direction, "level": round(current, 2)}
    except ImportError:
        return _adjust_volume_fallback(direction, steps)
    except Exception as exc:
        logger.error("Windows volume control failed: %s", exc)
        return _adjust_volume_fallback(direction, steps)


def _adjust_volume_fallback(direction: str, steps: int) -> Dict[str, Any]:
    if not _pyautogui_available:
        return {"success": False, "error": "No volume control backend available"}
    key = "volumemute" if direction == "mute" else f"volume{direction}"
    try:
        for _ in range(steps if direction != "mute" else 1):
            pyautogui.press(key)
        return {"success": True, "action": direction, "method": "media_keys", "steps": steps}
    except Exception as exc:
        logger.error("Volume fallback failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _adjust_volume(params: VolumeParams) -> Dict[str, Any]:
    direction = params.direction.strip().lower()
    if direction not in ("up", "down", "mute"):
        return {"success": False, "error": "direction must be 'up', 'down', or 'mute'"}
    system = platform.system()
    if system == "Windows":
        return _adjust_volume_windows(direction, params.steps)
    if system == "Darwin":
        script = {
            "up": f"set volume output volume ((output volume of (get volume settings)) + {params.steps * 5})",
            "down": f"set volume output volume ((output volume of (get volume settings)) - {params.steps * 5})",
            "mute": "set volume output muted true",
        }
        try:
            subprocess.run(["osascript", "-e", script[direction]], check=True, capture_output=True)
            return {"success": True, "action": direction, "method": "osascript"}
        except Exception as exc:
            return _adjust_volume_fallback(direction, params.steps)
    if system == "Linux":
        cmd = {
            "up": ["amixer", "-D", "pulse", "sset", "Master", f"{params.steps * 5}%+"],
            "down": ["amixer", "-D", "pulse", "sset", "Master", f"{params.steps * 5}%-"],
            "mute": ["amixer", "-D", "pulse", "sset", "Master", "toggle"],
        }
        try:
            subprocess.run(cmd[direction], check=True, capture_output=True)
            return {"success": True, "action": direction, "method": "amixer"}
        except Exception:
            return _adjust_volume_fallback(direction, params.steps)
    return _adjust_volume_fallback(direction, params.steps)


def _media_key(params: MediaKeyParams) -> Dict[str, Any]:
    action = params.action.strip().lower()
    key = _MEDIA_KEY_MAP.get(action)
    if not key:
        return {"success": False, "error": f"Unknown media action: {params.action}"}
    if not _pyautogui_available:
        return {"success": False, "error": "pyautogui not installed"}
    try:
        pyautogui.press(key)
        return {"success": True, "action": action}
    except Exception as exc:
        logger.error("media_key failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _play_audio_file(params: Dict[str, Any]) -> Dict[str, Any]:
    # [MODIFICATION]: Add audio file playback capability
    try:
        import subprocess
        import platform
        import os
        
        file_path = params.get("file_path", "")
        if not file_path or not isinstance(file_path, str):
            return {"success": False, "error": "Invalid file path"}
        
        if not os.path.exists(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}
        
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(["start", "", file_path], shell=True)
        elif system == "Darwin":
            subprocess.Popen(["afplay", file_path])
        else:
            subprocess.Popen(["xdg-open", file_path])
        
        return {"success": True, "file_path": file_path, "action": "playing"}
    except Exception as exc:
        logger.error("play_audio_file failed: %s", exc)
        return {"success": False, "error": str(exc)}


class PlayAudioParams(BaseModel):
    file_path: str = Field(min_length=1, description="Path to audio file to play")


def register_media_tools(registry) -> None:
    #Register media and volume control tools.
    registry.register_tool(
        name="adjust_volume",
        description="Adjust system volume up, down, or mute",
        params_model=VolumeParams,
        handler=_adjust_volume,
    )
    registry.register_tool(
        name="media_control",
        description="Control media playback (play_pause, next, previous, stop)",
        params_model=MediaKeyParams,
        handler=_media_key,
    )
    # [MODIFICATION]: Add audio file playback tool
    registry.register_tool(
        name="play_audio",
        description="Play an audio file using system media player",
        params_model=PlayAudioParams,
        handler=_play_audio_file,
    )
