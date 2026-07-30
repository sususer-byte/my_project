from core.assistant import Assistant
from core.voice_interface import VoiceInterface


def bootstrap_assistant(runtime):
    voice = VoiceInterface()
    runtime.container.voice = voice

    assistant = Assistant(container= runtime.container)
    runtime.container.assistant = assistant