from personality.personality_engine import PersonalityEngine
from emotion.emotion import Emotion
from emotion.emotion_analytics import EmotionAnalytics
from context.context import Context


def bootstrap_cognition(runtime):
    personality_engine = PersonalityEngine()
    runtime.container.personality_engine = personality_engine

    emotion = Emotion()
    runtime.container.emotion = emotion

    emotion_analytics = EmotionAnalytics()
    runtime.container.emotion_analytics = emotion_analytics

    context = Context(personality_engine=personality_engine)
    runtime.container.context = context