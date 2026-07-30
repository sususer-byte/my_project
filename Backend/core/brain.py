import json
import logging
import re
from typing import Any, Dict, List, Optional

from core.decision import (
    DecisionPlan,
    PreActionPlan,
    SpeechResponse,
    decision_json_schema,
    pre_action_json_schema,
    speech_response_json_schema,
    validate_decision_payload,
    validate_pre_action_payload,
    validate_speech_payload,
)

logger = logging.getLogger("furgal.brain")


class Brain:
    def __init__(self, provider_manager):
        self.provider_manager = provider_manager

    def think(self, messages):
        try:
            response = self.provider_manager.chat(messages=messages)
            reply = response.content
            return reply
        except Exception as exc:
            logger.error("Brain.think failed: %s", exc)
            raise

    def _chat_json(self, messages, schema, temperature = 0.1):
        return self.provider_manager.chat_json(messages= messages, schema = schema, options = {"temperature" :temperature, "num_ctx": 4096})

    def _extract_memory_with_rules(self, text):
        if not text or not isinstance(text, str):
            return None
        stripped = text.strip()
        lower = stripped.lower()
        if "?" in stripped and not any(
            phrase in lower
            for phrase in (
                "remember that",
                "please remember",
                "can you remember that",
            )
        ):
            return None

        name_match = re.search(
            r"\b(?:my name is|call me)\s+([A-Za-z][A-Za-z0-9_-]{1,40})\b",
            stripped,
            re.IGNORECASE,
        )
        if not name_match:
            name_match = re.search(
                r"\b(?:I am|I'm)\s+([A-Z][A-Za-z0-9_-]{1,40})\b",
                stripped,
            )
        if name_match:
            name = name_match.group(1).strip(".,! ")
            return {
                "text": f"The user's name is {name}",
                "category": "identity",
                "importance": 1.0,
                "confidence": 1.0,
            }

        preference_match = re.search(
            r"\bI\s+(love|like|prefer)\s+([^.!?\n]{2,80})",
            stripped,
            re.IGNORECASE,
        )
        if preference_match:
            verb = preference_match.group(1).lower()
            subject = preference_match.group(2).strip(" .,!")
            return {
                "text": f"The user {verb}s {subject}",
                "category": "interest" if verb in ("love", "like") else "preference",
                "importance": 0.8,
                "confidence": 1.0,
            }

        return None

    def extract_memory(self, text):
        try:
            rule_memory = self._extract_memory_with_rules(text)
            if rule_memory:
                return rule_memory

            memory = self.provider_manager.chat_json(
                messages=[
                    {
                        "role": "system",
                        "content": """
                You are a long-term memory extraction engine.

                Your job is to convert a user's message into ONE structured memory.

                Rules:

                - Extract only information explicitly stated.
                - Questions about existing memories are NOT memories.
                - Requests asking about previous information must return null.
                - Statements like "my name is ...", "my favorite ... is ...", or "I like ..." are long-term facts.
                - Questions like "do you remember my name?" or "what is my favorite ...?" are retrieval requests, not facts.
                - Never guess.
                - Never infer.
                - Never create information.
                - If there is no useful long-term memory, return exactly:

                null

                Otherwise return ONLY valid JSON.

                Schema:

                {
                "text":"",
                "category":"",
                "importance":0.0,
                "confidence":0.0
                }

                Categories:

                identity
                interest
                skill
                project
                preference
                goal
                relationship
                other

                Importance:

                1.0 = critical identity
                0.9 = long-term goals
                0.8 = important interests
                0.6 = useful facts
                0.3 = minor information

                Confidence:

                1.0 = explicitly stated
                0.5 = somewhat uncertain
                """,
                    },
                    {"role": "user", "content": text},
                ],
                options={"temperature": 0, "num_ctx": 4096},
            )
            if memory is None:
                return None 
            required = ["text", "category", "importance", "confidence"]
            for key in required:
                if key not in memory:
                    return None
            return memory
        except Exception as exc:
            logger.error("extract_memory failed: %s", exc)
            return None

    def merge_memories(self, memories):
        try:
            prompt = """
                You are a memory consolidation engine.

                Your task is to merge several memories into ONE single long-term memory sentence.

                Strict Rules:
                - Combine all distinct facts into a single, cohesive sentence using conjunctions (e.g., 'and', 'while', 'as well as').
                - Eliminate duplicate or redundant statements completely.
                - Retain every unique detail, entity, name, and preference exactly as provided.
                - Do not invent, infer, or extrapolate any information.
                - Do not output any introduction, explanation, or bullet points.
                - The output must be on a single line.

                Return ONLY in this exact format (on a single line):
                <merged_memory>User likes Python and robotics.</merged_memory>

                Memories:
                """
            user_content = "Memories to merge:\n"
            for memory in memories:
                user_content += f"- {memory['text']}\n"

            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content},
            ]

            raw_reply = self.think(messages).strip()
            match = re.search(r"<merged_memory>(.*?)</merged_memory>", raw_reply, re.DOTALL)
            if match:
                merged = match.group(1).strip()
                return merged if merged else None
            clean = raw_reply.replace("<merged_memory>", "").replace("</merged_memory>", "").strip()
            return clean if clean else None
        except Exception as exc:
            logger.error("merge_memories failed: %s", exc)
            return None

    def analyze_emotion(self, text):
        try:
            result = self.provider_manager.chat_json(
                messages=[
                    {
                        "role": "system",
                        "content": """
            Analyze the emotional tone of the user's message.
            Return ONLY valid JSON, nothing else:
            {
            "emotion": "happy/sad/angry/neutral",
            "intensity": 0.0
            }
            "intensity" must be a number between 0 and 1.
            If the message has no clear emotional content, return "neutral" with a low intensity.
            """,
                    },
                    {"role": "user", "content": text},
                ],
                schema={
                    "type": "object",
                    "properties":{
                        "emotion": {"type": "string"},
                        "intensity": {"type": "number"}
                    },
                    "required": ["emotion", "intensity"]
                },
                options={"temperature": 0, "num_ctx": 2048},
            )
            if "emotion" not in result or "intensity" not in result:
                return None
            if result["emotion"] not in ("happy", "sad", "angry", "neutral"):
                return None
            result["intensity"] = float(result["intensity"])
            if not (0.0 <= result["intensity"] <= 1.0):
                return None
            return result
        except Exception as exc:
            logger.error("analyze_emotion failed: %s", exc)
            return None

    def _build_facts_block(self, relevant_facts: List[Dict[str, Any]]) -> str:
        if not relevant_facts:
            return "- No directly relevant long-term facts.\n"
        facts_block = ""
        for item in relevant_facts:
            memory = item.get("memory", item)
            score = item.get("score", 0.0)
            category = memory.get("category", "memory")
            facts_block += f"- [{category}] {memory.get('text', '')} (relevance: {score:.2f})\n"
        return facts_block

    def plan_pre_actions(
        self,
        goal: str,
        relevant_facts: List[Dict[str, Any]],
        emotion_state: Dict[str, float],
        personality_traits: Dict[str, float],
        tool_schemas: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[PreActionPlan]:
        """Phase 1: decide perception/tool/robot actions BEFORE speaking."""
        try:
            schema = pre_action_json_schema()
            tools_block = json.dumps(tool_schemas or [], indent=2)
            facts_block = self._build_facts_block(relevant_facts)

            system_prompt = f"""
You are Furgal's perception-action planner for an embodied robot.

Return ONLY valid JSON matching this schema — no markdown, no explanation outside JSON:
{json.dumps(schema, indent=2)}

Rules:
- This is PHASE 1 only. Do NOT include any "speak" actions.
- Output "tool_call", "robot_move", or "vision_capture" actions ONLY when genuinely needed.
- If no pre-action is needed, return an empty "actions" array.
- Use "vision_capture" when the robot must see before responding.
- Use "tool_call" when an external tool from the registry is required.
- Use "robot_move" for physical motion commands.
- Never invent user facts.

Available tools (use exact tool_name values):
{tools_block}
"""

            user_prompt = f"""
Goal / user message:
{goal}

Relevant semantic memories:
{facts_block}

Current emotion state:
{json.dumps(emotion_state, indent=2)}

Current personality traits:
{json.dumps(personality_traits, indent=2)}

Produce the pre-action JSON plan for this turn.
"""

            payload = self._chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                schema=schema,
                temperature=0.1,
            )
            return validate_pre_action_payload(payload)
        except Exception as exc:
            logger.error("plan_pre_actions failed: %s", exc)
            return None

    def generate_speech(
        self,
        goal: str,
        relevant_facts: List[Dict[str, Any]],
        emotion_state: Dict[str, float],
        personality_traits: Dict[str, float],
        action_results: List[Dict[str, Any]],
        personality_modifier: Optional[str] = None,
    ) -> Optional[SpeechResponse]:
        """Phase 2: generate final speech AFTER pre-actions have executed."""
        try:
            schema = speech_response_json_schema()
            facts_block = self._build_facts_block(relevant_facts)
            results_block = json.dumps(action_results, indent=2, default=str)

            system_prompt = f"""
You are Furgal's speech generator for an embodied robot companion.

Return ONLY valid JSON matching this schema — no markdown, no explanation outside JSON:
{json.dumps(schema, indent=2)}

Rules:
- This is PHASE 2. Generate the final spoken reply based on REAL action results below.
- If vision was captured, reference what was observed from the action results.
- If a tool was called, incorporate the tool result into your reply.
- If no pre-actions ran, respond naturally to the user message.
- Keep speech conversational, 150-250 words max.
- Do not invent facts not supported by memories or action results.
"""

            modifier_block = ""
            if personality_modifier:
                modifier_block = f"\nPersonality guidance:\n{personality_modifier}\n"

            user_prompt = f"""
Goal / user message:
{goal}

Relevant semantic memories:
{facts_block}

Current emotion state:
{json.dumps(emotion_state, indent=2)}

Current personality traits:
{json.dumps(personality_traits, indent=2)}
{modifier_block}
Completed pre-action results (use this real data in your reply):
{results_block}

Produce the final speech JSON response.
"""

            payload = self._chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                schema=schema,
                temperature=0.3,
            )
            return validate_speech_payload(payload)
        except Exception as exc:
            logger.error("generate_speech failed: %s", exc)
            return None

    def plan_decision(
        self,
        goal: str,
        relevant_facts: List[Dict[str, Any]],
        emotion_state: Dict[str, float],
        personality_traits: Dict[str, float],
        tool_schemas: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[DecisionPlan]:
        """Legacy full-plan method — prefer two-phase plan_pre_actions + generate_speech."""
        try:
            schema = decision_json_schema()
            tools_block = json.dumps(tool_schemas or [], indent=2)
            facts_block = self._build_facts_block(relevant_facts)

            system_prompt = f"""
You are Furgal's high-level embodied decision planner for a physical robot companion.

Return ONLY valid JSON matching this schema — no markdown, no explanation outside JSON:
{json.dumps(schema, indent=2)}

Rules:
- Output a structured action list only.
- Use "tool_call" only when an external capability is genuinely needed.
- Use "robot_move" for physical motion via G-code/serial/ROS style commands.
- Use "vision_capture" when camera perception is required before acting.
- Include a "speak" action with the assistant reply text.
- Keep reasoning concise and grounded in provided facts.
- Do not invent user facts.

Available tools:
{tools_block}

Action types: speak, tool_call, robot_move, vision_capture
"""

            user_prompt = f"""
Goal / user message:
{goal}

Relevant semantic memories:
{facts_block}

Current emotion state:
{json.dumps(emotion_state, indent=2)}

Current personality traits:
{json.dumps(personality_traits, indent=2)}

Produce the JSON decision plan for this turn.
"""

            payload = self._chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                schema=schema,
                temperature=0.2,
            )
            return validate_decision_payload(payload)
        except Exception as exc:
            logger.error("plan_decision failed: %s", exc)
            return None
