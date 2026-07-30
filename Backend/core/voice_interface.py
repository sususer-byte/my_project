import logging
from typing import Optional 
logger = logging.getLogger("furgal.voice")


class VoiceInterface:
    

    def __init__(
        self,
        stt_language: str = "en-US",
        tts_rate: int = 175,
        tts_volume: float = 0.9,
    ):
        self.stt_language = stt_language
        self.tts_rate = tts_rate
        self.tts_volume = tts_volume
        self._recognizer = None
        self._microphone = None
        self._tts_engine = None
        self._stt_available = False
        self._tts_available = False
        self._init_stt()
        self._init_tts()

    @property
    def is_stt_available(self) -> bool:
        return self._stt_available

    @property
    def is_tts_available(self) -> bool:
        return self._tts_available

    @property
    def is_microphone_ready(self) -> bool:
        return self._stt_available and self._microphone is not None

    def _init_stt(self):
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 300
            self._recognizer.dynamic_energy_threshold = True
            self._microphone = sr.Microphone()
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
            self._stt_available = True
            logger.info("Speech-to-text initialized")
        except ImportError:
            logger.warning("speech_recognition not installed; voice input disabled")
            self._stt_available = False
        except Exception as exc:
            logger.warning("Microphone unavailable: %s — voice input disabled", exc)
            self._stt_available = False

    def _init_tts(self):
        try:
            import pyttsx3
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty("rate", self.tts_rate)
            self._tts_engine.setProperty("volume", self.tts_volume)
            self._tts_available = True
            logger.info("Text-to-speech initialized")
        except ImportError:
            logger.warning("pyttsx3 not installed; voice output disabled")
            self._tts_available = False
        except Exception as exc:
            logger.warning("TTS engine unavailable: %s", exc)
            self._tts_available = False

    def listen(self, timeout: float = 5.0, phrase_limit: float = 10.0) -> Optional[str]:
        """Listen from microphone and return transcribed text, or None on failure."""
        if not self._stt_available or self._recognizer is None or self._microphone is None:
            return None
        import speech_recognition as sr
        try:
            with self._microphone as source:
                logger.info("Listening... (speak now)")
                audio = self._recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit,
                )
            text = self._recognizer.recognize_google(audio, language=self.stt_language)
            logger.info("Recognized: %s", text)
            return text.strip() if text else None
        except sr.WaitTimeoutError:
            logger.debug("Listen timeout — no speech detected")
            return None
        except sr.UnknownValueError:
            logger.debug("Could not understand audio")
            return None
        except sr.RequestError as exc:
            logger.error("STT service error: %s", exc)
            return None
        except Exception as exc:
            logger.error("listen failed: %s", exc)
            return None

    def speak(self, text: str) -> bool:
        """Convert text to speech and play through speakers."""
        if not text or not self._tts_available or self._tts_engine is None:
            return False
        try:
            self._tts_engine.say(text)
            self._tts_engine.runAndWait()
            return True
        except Exception as exc:
            logger.error("speak failed: %s", exc)
            return False

    def get_mode_description(self) -> str:
        if self.is_microphone_ready:
            return "voice+keyboard"
        return "keyboard"
