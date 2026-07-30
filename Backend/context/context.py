from personality.personality import SYSTEM_PROMPT


class Context:
    def __init__(self, personality_engine=None):
        self.system_prompt = SYSTEM_PROMPT
        self.personality_engine = personality_engine

    def build(
        self,
        messages,
        memories,
        user_input,
        emotion_state=None,
        personality_modifier=None,
    ):
        context = [{
            "role": "system",
            "content": self.system_prompt,
        }]

        modifier = personality_modifier
        if not modifier and self.personality_engine is not None:
            modifier = self.personality_engine.get_modifier_text()
        if modifier:
            context.append({
                "role": "system",
                "content": modifier,
            })

        if emotion_state:
            mood_text = (
                "Internal mood state (for tone only, never mention these "
                "numbers to the user):\n"
                f"happy={emotion_state.get('happy', 0):.2f}, "
                f"sad={emotion_state.get('sad', 0):.2f}, "
                f"angry={emotion_state.get('angry', 0):.2f}, "
                f"stress={emotion_state.get('stress', 0):.2f}, "
                f"energy={emotion_state.get('energy', 0):.2f}, "
                f"curiosity={emotion_state.get('curiosity', 0):.2f}\n"
                "Let this subtly color your tone. It must NEVER override "
                "user facts or the personality rules above."
            )
            context.append({
                "role": "system",
                "content": mood_text,
            })

        if memories:
            memory_text = (
                "The following are long-term memories. "
                "They may or may not be relevant. "
                "Use ONLY if they help answer the user's message. "
                "Ignore irrelevant memories.\n"
            )
            for item in memories:
                score = item["score"]
                memory = item["memory"]
                category = memory.get("category", "memory")
                memory_text += f"- [{category}] {memory['text']} (relevance:{score:.2f})\n"
            context.append({
                "role": "system",
                "content": memory_text,
            })

        recent = messages[-10:]
        if recent and recent[-1].get("role") == "user" and recent[-1].get("content") == user_input:
            recent = recent[:-1]
        context.extend(recent)
        context.append({
            "role": "user",
            "content": user_input,
        })
        return context
