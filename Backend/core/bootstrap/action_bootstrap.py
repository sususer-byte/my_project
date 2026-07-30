from action.executor import ActionExecutor
from action.tool_registry import build_default_tool_registry
from action.vision import VisionProcessor
from action.controller import RobotController
from core.planner import Planner


def bootstrap_action(runtime):

    tool_registry = build_default_tool_registry()
    runtime.container.tool_registry = tool_registry

    action_executor = ActionExecutor(tool_registry=tool_registry, vision=VisionProcessor(),controller=RobotController(simulate=True), )
    runtime.container.action_executor = action_executor

    planner = Planner(runtime.container.brain, tool_registry=tool_registry)
    runtime.container.planner = planner