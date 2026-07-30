#Central tool registry with Pydantic validation and dynamic JSON schema export.

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type

from pydantic import BaseModel

from action.tools.safeguards import validate_safe_args
from action.tools import (
    register_os_tools,
    register_file_tools,
    register_media_tools,
    register_web_tools,
    register_network_tools,
)

logger = logging.getLogger("furgal.action.tools")


@dataclass
class ToolEntry:
    name: str
    description: str
    params_model: Type[BaseModel]
    handler: Callable[[BaseModel], Any]


class ToolRegistry:
    #Registers tools, validates arguments via Pydantic, and exports LLM schemas.

    def __init__(self):
        self._tools: Dict[str, ToolEntry] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        params_model: Type[BaseModel],
        handler: Callable[[BaseModel], Any],
    ) -> None:
        if not name or not name.strip():
            raise ValueError("Tool name is required")
        if not callable(handler):
            raise ValueError(f"Handler for tool '{name}' must be callable")
        key = name.strip().lower()
        self._tools[key] = ToolEntry(
            name=key,
            description=description.strip(),
            params_model=params_model,
            handler=handler,
        )
        logger.info("Registered tool: %s", key)

    def list_tools(self) -> List[str]:
        return sorted(self._tools.keys())

    def get_tool(self, name: str) -> Optional[ToolEntry]:
        return self._tools.get((name or "").strip().lower())

    def invoke(self, name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        key = (name or "").strip().lower()
        entry = self._tools.get(key)
        if entry is None:
            return {
                "success": False,
                "error": f"Unknown tool: {name}",
                "available": self.list_tools(),
            }

        payload = args if isinstance(args, dict) else {}
        safety_error = validate_safe_args(payload)
        if safety_error:
            logger.warning("Blocked unsafe tool args for %s: %s", key, safety_error)
            return {"success": False, "error": safety_error}

        try:
            validated = entry.params_model.model_validate(payload)
        except Exception as exc:
            logger.error("Tool %s validation failed: %s", key, exc)
            return {"success": False, "error": f"Invalid arguments for tool '{key}': {exc}"}

        try:
            result = entry.handler(validated)
            if isinstance(result, dict) and "success" in result:
                return {"success": result.get("success", False), "tool": key, "result": result}
            return {"success": True, "tool": key, "result": result}
        except Exception as exc:
            logger.error("Tool %s execution failed: %s", key, exc)
            return {"success": False, "error": str(exc)}

    def export_json_schemas(self) -> List[Dict[str, Any]]:
        """Export tool definitions as JSON Schema for LLM system prompts."""
        schemas = []
        for entry in self._tools.values():
            param_schema = entry.params_model.model_json_schema()
            schemas.append({
                "name": entry.name,
                "description": entry.description,
                "parameters": param_schema,
            })
        return schemas


class GetTimeParams(BaseModel):
    """No parameters required."""


class SystemInfoParams(BaseModel):
    """No parameters required."""


def _get_time(_params: GetTimeParams) -> str:
    return datetime.now().isoformat()


def _system_info(_params: SystemInfoParams) -> Dict[str, Any]:
    import platform
    return {
        "platform": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
    }


def build_default_tool_registry() -> ToolRegistry:
    """Build the full default tool registry with all available modules."""
    registry = ToolRegistry()
    registry.register_tool(
        name="get_time",
        description="Get the current local date and time in ISO format",
        params_model=GetTimeParams,
        handler=_get_time,
    )
    registry.register_tool(
        name="system_info",
        description="Get basic system information (OS, release, architecture)",
        params_model=SystemInfoParams,
        handler=_system_info,
    )
    register_os_tools(registry)
    register_file_tools(registry)
    register_media_tools(registry)
    register_web_tools(registry)
    register_network_tools(registry)
    return registry
