"""Furgal AI tool implementations — OS, file, media, web, and network layers."""

from action.tools.os_control import register_os_tools
from action.tools.file_management import register_file_tools
from action.tools.media_control import register_media_tools
from action.tools.web_control import register_web_tools
from action.tools.network_connectivity import register_network_tools

__all__ = [
    "register_os_tools",
    "register_file_tools",
    "register_media_tools",
    "register_web_tools",
    "register_network_tools",
]
