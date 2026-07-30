import logging

from typing import Any, Dict, List



from core.decision import ActionType, DecisionPlan, PreActionPlan

from action.tool_registry import ToolRegistry

from action.vision import VisionProcessor

from action.controller import RobotController



logger = logging.getLogger("furgal.action.executor")





class ActionExecutor:

    def __init__(

        self,

        tool_registry: ToolRegistry,

        vision: VisionProcessor,

        controller: RobotController,

    ):

        self.tools = tool_registry

        self.vision = vision

        self.controller = controller



    def _execute_action(self, action) -> Dict[str, Any]:

        #Execute a single planned action and return its result.

        if action.action_type == ActionType.SPEAK:

            return {

                "success": True,

                "action_type": action.action_type.value,

                "speech": action.speech,

            }

        if action.action_type == ActionType.TOOL_CALL:

            result = self.tools.invoke(action.tool_name, action.tool_args)

            return {

                "success": result.get("success", False),

                "action_type": action.action_type.value,

                "tool_name": action.tool_name,

                "details": result,

            }

        if action.action_type == ActionType.ROBOT_MOVE:

            result = self.controller.send_command(action.robot_command or "")

            return {

                "success": result.get("success", False),

                "action_type": action.action_type.value,

                "details": result,

            }

        if action.action_type == ActionType.VISION_CAPTURE:

            result = self.vision.analyze_task(action.vision_task or "observe")

            return {

                "success": result.get("success", False),

                "action_type": action.action_type.value,

                "details": result,

            }

        return {

            "success": False,

            "action_type": str(action.action_type),

            "error": "Unsupported action type",

        }



    def execute_pre_actions(self, plan: PreActionPlan) -> List[Dict[str, Any]]:

        """Phase 1: execute perception/tool/robot actions only — no speak."""

        results: List[Dict[str, Any]] = []

        if plan is None:

            return results



        for action in plan.actions:

            if action.action_type == ActionType.SPEAK:

                logger.warning("Skipping speak action in pre-action phase")

                continue

            try:

                results.append(self._execute_action(action))

            except Exception as exc:

                logger.error("Failed to execute pre-action %s: %s", action.action_type, exc)

                results.append({

                    "success": False,

                    "action_type": action.action_type.value,

                    "error": str(exc),

                })

        return results



    def execute_plan(self, plan: DecisionPlan) -> List[Dict[str, Any]]:

        """Legacy: execute all actions in a full decision plan."""

        results: List[Dict[str, Any]] = []

        if plan is None:

            return [{"success": False, "error": "No decision plan provided"}]



        for action in plan.actions:

            try:

                results.append(self._execute_action(action))

            except Exception as exc:

                logger.error("Failed to execute action %s: %s", action.action_type, exc)

                results.append({

                    "success": False,

                    "action_type": action.action_type.value,

                    "error": str(exc),

                })

        return results


