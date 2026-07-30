import logging
from typing import Any, Dict, List, Optional

from core.decision import PreActionPlan, SpeechResponse

logger = logging.getLogger("furgal.planner")


class Planner:
    def __init__(self, brain, tool_registry=None):
        if brain is None:
            raise ValueError("Planner requires a Brain instance")
        self.brain = brain
        self.tool_registry = tool_registry

    def _tool_schemas(self) -> List[Dict[str, Any]]:
        if self.tool_registry is None:
            return []
        try:
            return self.tool_registry.export_json_schemas()
        except Exception as exc:
            logger.error("Failed to export tool schemas: %s", exc)
            return []

    def build_goal(self, user_input: str, recent_messages: List[Dict[str, str]]) -> str:
        try:
            if not user_input or not isinstance(user_input, str):
                return ""
            context_hint = ""
            if recent_messages:
                last_assistant = next(
                    (
                        message["content"]
                        for message in reversed(recent_messages)
                        if message.get("role") == "assistant"
                    ),
                    None,
                )
                if last_assistant:
                    context_hint = f"\nPrevious assistant reply context: {last_assistant[:200]}"
            return f"Respond to the user and decide embodied actions for: {user_input.strip()}{context_hint}"
        except Exception as exc:
            logger.error("build_goal failed: %s", exc)
            return user_input or ""

    def _is_memory_lookup(self, user_input: str) -> bool:
        text = (user_input or "").lower()
        lookup_phrases = (
            "my name",
            "remember me",
            "who am i",
            "what do i like",
            "what i like",
            "do i like",
            "do i love",
            "favorite",
            "favourite",
        )
        action_phrases = (
            "open",
            "search",
            "google",
            "browse",
            "take a picture",
            "photo",
            "camera",
            "capture",
            "move",
            "turn",
            "play",
            "pause",
            "file",
            "folder",
        )
        return any(phrase in text for phrase in lookup_phrases) and not any(
            phrase in text for phrase in action_phrases
        )

    def plan_pre_actions(
        self,
        user_input: str,
        relevant_facts: List[Dict[str, Any]],
        emotion_state: Dict[str, float],
        personality_traits: Dict[str, float],
        recent_messages: Optional[List[Dict[str, str]]] = None,
    ) -> PreActionPlan:
        """Phase 1: perception / tool / robot actions only."""
        goal = self.build_goal(user_input, recent_messages or [])
        if self._is_memory_lookup(user_input):
            return PreActionPlan(
                reasoning="Memory lookup question; no pre-action needed.",
                goal_summary=goal or "Answer memory question",
                actions=[],
            )
        plan = self.brain.plan_pre_actions(
            goal=goal,
            relevant_facts=relevant_facts,
            emotion_state=emotion_state or {},
            personality_traits=personality_traits or {},
            tool_schemas=self._tool_schemas(),
        )
        if plan is not None:
            return plan
        logger.warning("Pre-action planning failed; returning empty pre-action plan")
        return PreActionPlan(
            reasoning="No pre-actions needed or planning unavailable.",
            goal_summary=goal or "Respond to user",
            actions=[],
        )

    def generate_reply(
        self,
        user_input: str,
        relevant_facts: List[Dict[str, Any]],
        emotion_state: Dict[str, float],
        personality_traits: Dict[str, float],
        action_results: List[Dict[str, Any]],
        recent_messages: Optional[List[Dict[str, str]]] = None,
        personality_modifier: Optional[str] = None,
    ) -> str:
        """Phase 2: generate speech after pre-actions have completed."""
        goal = self.build_goal(user_input, recent_messages or [])
        speech = self.brain.generate_speech(
            goal=goal,
            relevant_facts=relevant_facts,
            emotion_state=emotion_state or {},
            personality_traits=personality_traits or {},
            action_results=action_results or [],
            personality_modifier=personality_modifier,
        )
        if speech is not None:
            return speech.speech.strip()
        logger.warning("Speech generation failed; using fallback reply")
        return "I'm here with you. I had trouble forming a reply, but I'm still listening."

    def extract_speech_from_response(self, speech: Optional[SpeechResponse]) -> str:
        if speech is None:
            return "I understood your message, but I need a moment to form a proper reply."
        return speech.speech.strip()
