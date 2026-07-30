import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger("furgal.decision")

PRE_ACTION_TYPES = frozenset({"tool_call", "robot_move", "vision_capture"})


class ActionType(str, Enum):
    SPEAK = "speak"
    TOOL_CALL = "tool_call"
    ROBOT_MOVE = "robot_move"
    VISION_CAPTURE = "vision_capture"


class PlannedAction(BaseModel):
    action_type: ActionType
    speech: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    robot_command: Optional[str] = None
    vision_task: Optional[str] = None
    priority: int = Field(default=1, ge=1, le=10)

    @model_validator(mode="after")
    def validate_action_payload(self):
        if self.action_type == ActionType.SPEAK and not (self.speech and self.speech.strip()):
            raise ValueError("speak actions require non-empty speech")
        if self.action_type == ActionType.TOOL_CALL:
            if not self.tool_name or not self.tool_name.strip():
                raise ValueError("tool_call actions require tool_name")
            if self.tool_args is None:
                self.tool_args = {}
        if self.action_type == ActionType.ROBOT_MOVE and not (self.robot_command and self.robot_command.strip()):
            raise ValueError("robot_move actions require robot_command")
        if self.action_type == ActionType.VISION_CAPTURE and not (self.vision_task and self.vision_task.strip()):
            raise ValueError("vision_capture actions require vision_task")
        return self


class PreActionPlan(BaseModel):
    """Perception / pre-action phase — no speak actions allowed."""

    reasoning: str = Field(min_length=1)
    goal_summary: str = Field(min_length=1)
    actions: List[PlannedAction] = Field(default_factory=list)

    @field_validator("actions")
    @classmethod
    def reject_speak_actions(cls, actions):
        for action in actions:
            if action.action_type == ActionType.SPEAK:
                raise ValueError("PreActionPlan must not contain speak actions")
        return sorted(actions, key=lambda item: item.priority)


class SpeechResponse(BaseModel):
    """Final speech phase — generated after pre-actions complete."""

    reasoning: str = Field(min_length=1)
    speech: str = Field(min_length=1)


class DecisionPlan(BaseModel):
    reasoning: str = Field(min_length=1)
    goal_summary: str = Field(min_length=1)
    actions: List[PlannedAction] = Field(min_length=1)

    @field_validator("actions")
    @classmethod
    def ensure_sorted_priority(cls, actions):
        if not actions:
            raise ValueError("actions must not be empty")
        return sorted(actions, key=lambda item: item.priority)


def validate_decision_payload(payload: Any) -> Optional[DecisionPlan]:
    return _validate_model(payload, DecisionPlan)


def validate_pre_action_payload(payload: Any) -> Optional[PreActionPlan]:
    return _validate_model(payload, PreActionPlan)


def validate_speech_payload(payload: Any) -> Optional[SpeechResponse]:
    return _validate_model(payload, SpeechResponse)


def _validate_model(payload: Any, model_cls):
    if payload is None:
        logger.warning("%s payload is None", model_cls.__name__)
        return None
    try:
        if isinstance(payload, dict):
            return model_cls.model_validate(payload)
        if isinstance(payload, str):
            return model_cls.model_validate_json(payload)
        logger.warning("Unsupported payload type for %s: %s", model_cls.__name__, type(payload))
        return None
    except Exception as exc:
        logger.error("%s validation failed: %s", model_cls.__name__, exc)
        return None


def decision_json_schema() -> dict:
    return DecisionPlan.model_json_schema()


def pre_action_json_schema() -> dict:
    return PreActionPlan.model_json_schema()


def speech_response_json_schema() -> dict:
    return SpeechResponse.model_json_schema()
