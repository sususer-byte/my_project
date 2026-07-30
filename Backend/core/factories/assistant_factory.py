from core.assistant import Assistant


def create_assistant(container):
    return Assistant(
        memory=container.memory,
        memory_manager=container.memory_manager,
        brain=container.brain,
        context=container.context,
        emotion=container.emotion,
        emotion_analytics=container.emotion_analytics,
        personality_engine=container.personality_engine,
        consolidation=container.consolidation,
        lifecycle=container.memory_lifecycle,
        validator=container.validator,
        planner=container.planner,
        action_executor=container.action_executor,
        background_worker=container.background_worker,
        voice_interface=container.voice,
    )