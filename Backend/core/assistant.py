import logging

logger = logging.getLogger("furgal.assistant")


class Assistant:
    # [MODIFICATION]: Refactor to use proper dependency injection instead of direct container access
    def __init__(self, container):
        self.container = container
        
        # [MODIFICATION]: Use dependency injection pattern for better decoupling
        self._inject_dependencies(container)

    def _inject_dependencies(self, container):
        """Inject dependencies using container's dependency injection system"""
        # [MODIFICATION]: Get services through container interface rather than direct access
        self.context = container.get("context")
        self.memory = container.get("memory")
        self.memory_manager = container.get("memory_manager")
        self.validator = container.get("validator")
        self.emotion = container.get("emotion")
        self.emotion_analytics = container.get("emotion_analytics")
        self.personality_engine = container.get("personality_engine")
        self.consolidation = container.get("consolidation")
        self.lifecycle = container.get("memory_lifecycle")
        self.brain = container.get("brain")
        self.action_executor = container.get("action_executor")
        self.planner = container.get("planner")
        self.background_worker = container.get("background_worker")
        self.voice = container.get("voice")
        
        # [MODIFICATION]: Access tool registry through action executor interface
        self.tool_registry = self.action_executor.tools if self.action_executor else None

    def start_background_workers(self):
        if self.background_worker and not self.background_worker.is_running:
            self.background_worker.start()
            logger.info("Background memory worker started")

    def stop_background_workers(self):
        if self.background_worker and self.background_worker.is_running:
            self.background_worker.stop()
            logger.info("Background memory worker stopped")

    def _remember(self, text):
        try:
            extracted_memory = self.brain.extract_memory(text)
            if not self.validator.validate(extracted_memory):
                return
            stored = self.memory_manager.add_memory(
                text=extracted_memory["text"],
                category=extracted_memory["category"],
                importance=extracted_memory["importance"],
                confidence=extracted_memory["confidence"],
            )
            if stored:
                self.consolidation.consolidate_and_merge(
                    self.brain, self.memory_manager, stored
                )
        except Exception as exc:
            logger.warning("Không thể lưu trí nhớ: %s", exc)

    def _update_emotion(self, text):
        try:
            self.emotion.decay()
            result = self.brain.analyze_emotion(text)
            self.emotion.update(result)
            snapshot = self.emotion.snapshot_for_analytics()
            self.emotion_analytics.record_snapshot(snapshot)
            self.personality_engine.update_from_emotion_analytics(self.emotion_analytics)
        except Exception as exc:
            logger.warning("Không thể phân tích cảm xúc: %s", exc)

    def chat(self, text):
        """Process a user message through the two-phase perception-action loop."""
        self.memory.add_message("user", text)

        self._remember(text)
        self._update_emotion(text)

        relevant_facts = self.memory_manager.retrieve_memory(text)
        emotion_state = self.emotion.state()
        personality_traits = self.personality_engine.get_traits()
        recent_messages = self.memory.get_recent_messages()
        personality_modifier = self.personality_engine.get_modifier_text()

        try:
            pre_plan = self.planner.plan_pre_actions(
                user_input=text,
                relevant_facts=relevant_facts,
                emotion_state=emotion_state,
                personality_traits=personality_traits,
                recent_messages=recent_messages,
            )
            action_results = self.action_executor.execute_pre_actions(pre_plan)
            if action_results:
                logger.info("Executed %d pre-actions before speech", len(action_results))

            reply = self.planner.generate_reply(
                user_input=text,
                relevant_facts=relevant_facts,
                emotion_state=emotion_state,
                personality_traits=personality_traits,
                action_results=action_results,
                recent_messages=recent_messages,
                personality_modifier=personality_modifier,
            )
        except Exception as exc:
            logger.error("Lỗi khi lập kế hoạch/thực thi: %s", exc)
            try:
                messages = self.context.build(
                    recent_messages,
                    relevant_facts,
                    text,
                    emotion_state,
                    personality_modifier,
                )
                reply = self.brain.think(messages)
            except Exception as fallback_exc:
                logger.error("Lỗi khi sinh câu trả lời: %s", fallback_exc)
                reply = "Sorry, my system seems to be malfunctioned"

        self.memory.add_message("assistant", reply)

        if self.voice and self.voice.is_tts_available:
            try:
                self.voice.speak(reply)
            except Exception as exc:
                logger.warning("TTS playback failed: %s", exc)

        return reply

    def listen_once(self, timeout: float = 5.0, phrase_limit: float = 10.0):
        """Attempt voice input; returns transcribed text or None."""
        if self.voice is None or not self.voice.is_stt_available:
            return None
        try:
            return self.voice.listen(timeout=timeout, phrase_limit=phrase_limit)
        except Exception as exc:
            logger.warning("Voice listen failed: %s", exc)
            return None
