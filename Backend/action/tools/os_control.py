#OS-level control: process management, keystrokes, and hotkeys.

import logging
import platform
import re
import subprocess
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("furgal.action.tools")

_psutil_available = False
_pyautogui_available = False
_SAFE_APP_RE = re.compile(r"^[\w\s.\-:/\\()]+$")
_ALLOWED_HOTKEYS = {
    "alt", "backspace", "ctrl", "delete", "down", "end", "esc", "escape",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
    "home", "left", "pagedown", "pageup", "right", "shift", "space", "tab", "up",
}
_PROTECTED_PROCESS_NAMES = {
    "cmd.exe", "conhost.exe", "csrss.exe", "dwm.exe", "explorer.exe",
    "lsass.exe", "powershell.exe", "python.exe", "pythonw.exe",
    "services.exe", "smss.exe", "svchost.exe", "system", "wininit.exe",
    "winlogon.exe",
}

try:
    import psutil
    _psutil_available = True
except ImportError:
    logger.warning("psutil not installed; process management limited")

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    _pyautogui_available = True
except ImportError:
    logger.warning("pyautogui not installed; UI automation unavailable")


class OpenAppParams(BaseModel):
    app_name: str = Field(min_length=1, max_length=160, description="Application name or executable to launch")


class CloseAppParams(BaseModel):
    app_name: str = Field(min_length=1, max_length=80, description="Application name to close")
    force: bool = Field(default=False, description="Force-kill the process")


class ListProcessesParams(BaseModel):
    name_filter: Optional[str] = Field(default=None, description="Optional substring to filter process names")


class TypeTextParams(BaseModel):
    text: str = Field(min_length=1, max_length=2000, description="Text to type via keyboard simulation")
    interval: float = Field(default=0.02, ge=0.0, le=1.0, description="Delay between keystrokes")


class HotkeyParams(BaseModel):
    keys: List[str] = Field(min_length=1, max_length=4, description="Key combination, e.g. ['ctrl', 'c']")

    @field_validator("keys")
    @classmethod
    def validate_keys(cls, keys):
        cleaned = []
        for key in keys:
            normalized = str(key).strip().lower()
            if not normalized:
                raise ValueError("Hotkey names must be non-empty")
            if normalized not in _ALLOWED_HOTKEYS and len(normalized) != 1:
                raise ValueError(f"Hotkey is not allowed: {key}")
            cleaned.append(normalized)
        return cleaned


def _open_app(params: OpenAppParams) -> Dict[str, Any]:
    # [MODIFICATION]: Enhanced app opening with better error handling and validation
    name = params.app_name.strip()
    if not _SAFE_APP_RE.fullmatch(name):
        return {"success": False, "error": "App name contains unsafe characters"}
    
    system = platform.system()
    try:
        if system == "Windows":
            # [MODIFICATION]: Better Windows app launching
            if name.endswith('.exe'):
                subprocess.Popen([name], shell=False)
            else:
                subprocess.Popen(["cmd", "/c", "start", "", name], shell=False)
        elif system == "Darwin":
            # [MODIFICATION]: Enhanced macOS app opening
            if name.endswith('.app'):
                subprocess.Popen(["open", name])
            else:
                subprocess.Popen(["open", "-a", name])
        else:
            # [MODIFICATION]: Better Linux/Unix app handling
            try:
                subprocess.Popen(["xdg-open", name])
            except FileNotFoundError:
                subprocess.Popen([name], shell=False)
        
        logger.info("Successfully opened app: %s", name)
        return {"success": True, "app_name": name, "action": "opened", "platform": system}
    except Exception as exc:
        logger.error("open_app failed: %s", exc)
        return {"success": False, "error": str(exc), "app_name": name}


def _close_app(params: CloseAppParams) -> Dict[str, Any]:
    if not _psutil_available:
        return {"success": False, "error": "psutil not installed"}
    name = params.app_name.strip().lower()
    if name in _PROTECTED_PROCESS_NAMES or f"{name}.exe" in _PROTECTED_PROCESS_NAMES:
        return {"success": False, "error": f"Refusing to close protected process: {params.app_name}"}
    closed = []
    try:
        for proc in psutil.process_iter(["pid", "name"]):
            proc_name = (proc.info.get("name") or "").lower()
            if proc_name in _PROTECTED_PROCESS_NAMES:
                continue
            if name == proc_name or name == proc_name.removesuffix(".exe"):
                if params.force:
                    proc.kill()
                else:
                    proc.terminate()
                closed.append(proc.info["pid"])
        if not closed:
            return {"success": False, "error": f"No process matching '{params.app_name}' found"}
        time.sleep(0.3)
        return {"success": True, "closed_pids": closed}
    except Exception as exc:
        logger.error("close_app failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _list_processes(params: ListProcessesParams) -> Dict[str, Any]:
    if not _psutil_available:
        return {"success": False, "error": "psutil not installed"}
    try:
        processes = []
        filt = (params.name_filter or "").lower()
        for proc in psutil.process_iter(["pid", "name", "status"]):
            name = proc.info.get("name") or ""
            if filt and filt not in name.lower():
                continue
            processes.append({
                "pid": proc.info["pid"],
                "name": name,
                "status": proc.info.get("status"),
            })
        return {"success": True, "count": len(processes), "processes": processes[:50]}
    except Exception as exc:
        logger.error("list_processes failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _type_text(params: TypeTextParams) -> Dict[str, Any]:
    if not _pyautogui_available:
        return {"success": False, "error": "pyautogui not installed"}
    try:
        pyautogui.write(params.text, interval=params.interval)
        return {"success": True, "typed_length": len(params.text)}
    except Exception as exc:
        logger.error("type_text failed: %s", exc)
        return {"success": False, "error": str(exc)}


def _hotkey(params: HotkeyParams) -> Dict[str, Any]:
    if not _pyautogui_available:
        return {"success": False, "error": "pyautogui not installed"}
    try:
        pyautogui.hotkey(*params.keys)
        return {"success": True, "keys": params.keys}
    except Exception as exc:
        logger.error("hotkey failed: %s", exc)
        return {"success": False, "error": str(exc)}


def register_os_tools(registry) -> None:
    """Register OS control tools with the given registry."""
    registry.register_tool(
        name="open_app",
        description="Open/launch an application by name or executable path",
        params_model=OpenAppParams,
        handler=_open_app,
    )
    registry.register_tool(
        name="close_app",
        description="Close a running application by name",
        params_model=CloseAppParams,
        handler=_close_app,
    )
    registry.register_tool(
        name="list_processes",
        description="List running processes, optionally filtered by name",
        params_model=ListProcessesParams,
        handler=_list_processes,
    )
    registry.register_tool(
        name="type_text",
        description="Simulate keyboard typing of text into the active window",
        params_model=TypeTextParams,
        handler=_type_text,
    )
    registry.register_tool(
        name="hotkey",
        description="Press a keyboard shortcut (e.g. ctrl+c, alt+tab)",
        params_model=HotkeyParams,
        handler=_hotkey,
    )
