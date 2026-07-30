import json
import logging
import os
import threading
from datetime import datetime

logger = logging.getLogger("furgal.personality")

PERSONALITY_FILE = "storage/personality.json"
DRIFT_RATE = 0.015
MIN_TRAIT = 0.05
MAX_TRAIT = 0.95


class PersonalityEngine:
    DEFAULT_TRAITS = {
        "humor": 0.72,
        "warmth": 0.65,
        "playfulness": 0.78,
        "seriousness": 0.28,
    }

    def __init__(self, file_path=PERSONALITY_FILE, drift_rate=DRIFT_RATE):
        self.file_path = file_path
        self.drift_rate = drift_rate
        self._lock = threading.RLock()
        self._ensure_storage_dir()
        self.traits = self._load_or_create()

    def _ensure_storage_dir(self):
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def _load_or_create(self):
        try:
            if not os.path.exists(self.file_path):
                traits = dict(self.DEFAULT_TRAITS)
                self._write_file(traits)
                return traits
            with open(self.file_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if not isinstance(loaded, dict):
                raise ValueError("Personality file must contain a JSON object")
            merged = dict(self.DEFAULT_TRAITS)
            for key in merged:
                if key in loaded:
                    try:
                        merged[key] = float(loaded[key])
                    except (TypeError, ValueError):
                        logger.warning("Invalid trait value for %s", key)
            return self._clamp_traits(merged)
        except Exception as exc:
            logger.error("Failed to load personality traits: %s", exc)
            return dict(self.DEFAULT_TRAITS)

    def _write_file(self, traits):
        tmp_path = f"{self.file_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(traits, handle, indent=4)
        os.replace(tmp_path, self.file_path)

    def _clamp(self, value):
        return max(MIN_TRAIT, min(MAX_TRAIT, float(value)))

    def _clamp_traits(self, traits):
        return {key: self._clamp(traits.get(key, default)) for key, default in self.DEFAULT_TRAITS.items()}

    def get_traits(self):
        with self._lock:
            return dict(self.traits)

    def save(self):
        with self._lock:
            try:
                self._write_file(self.traits)
            except Exception as exc:
                logger.error("Failed to save personality traits: %s", exc)

    def apply_drift(self, drift_signals):
        if not drift_signals or not isinstance(drift_signals, dict):
            return

        with self._lock:
            try:
                warmth_target = float(drift_signals.get("warmth_signal", 0.5))
                humor_target = float(drift_signals.get("humor_signal", 0.5))
                play_target = float(drift_signals.get("playfulness_signal", 0.5))
                serious_target = float(drift_signals.get("seriousness_signal", 0.5))

                self.traits["warmth"] = self._clamp(
                    self.traits["warmth"] + (warmth_target - self.traits["warmth"]) * self.drift_rate
                )
                self.traits["humor"] = self._clamp(
                    self.traits["humor"] + (humor_target - self.traits["humor"]) * self.drift_rate
                )
                self.traits["playfulness"] = self._clamp(
                    self.traits["playfulness"] + (play_target - self.traits["playfulness"]) * self.drift_rate
                )
                self.traits["seriousness"] = self._clamp(
                    self.traits["seriousness"] + (serious_target - self.traits["seriousness"]) * self.drift_rate
                )
                self.save()
            except Exception as exc:
                logger.error("Personality drift failed: %s", exc)

    def get_modifier_text(self):
        traits = self.get_traits()
        humor = traits["humor"]
        warmth = traits["warmth"]
        playfulness = traits["playfulness"]
        seriousness = traits["seriousness"]

        tone_hints = []
        if humor >= 0.7:
            tone_hints.append("Use light wit and gentle sarcasm when appropriate.")
        elif humor <= 0.35:
            tone_hints.append("Keep humor minimal; stay straightforward.")
        if warmth >= 0.7:
            tone_hints.append("Be warmly supportive and emotionally present.")
        elif warmth <= 0.35:
            tone_hints.append("Stay polite but emotionally reserved.")
        if playfulness >= 0.7:
            tone_hints.append("Allow playful curiosity and creative phrasing.")
        elif playfulness <= 0.35:
            tone_hints.append("Favor direct, practical responses over playfulness.")
        if seriousness >= 0.6:
            tone_hints.append("Prioritize clarity and grounded seriousness.")
        elif seriousness <= 0.25:
            tone_hints.append("Keep the conversation relaxed and informal.")

        hints_block = "\n".join(f"- {hint}" for hint in tone_hints) if tone_hints else "- Maintain balanced companion tone."

        return (
            "Dynamic personality modifiers (internal guidance only — never mention these numbers):\n"
            f"humor={humor:.2f}, warmth={warmth:.2f}, "
            f"playfulness={playfulness:.2f}, seriousness={seriousness:.2f}\n"
            "Tone directives:\n"
            f"{hints_block}\n"
            "These traits drift slowly from long-term emotional history. "
            "They must NEVER override user facts or safety constraints."
        )

    def update_from_emotion_analytics(self, emotion_analytics):
        try:
            signals = emotion_analytics.get_personality_drift_signals()
            self.apply_drift(signals)
        except Exception as exc:
            logger.error("Failed to update personality from analytics: %s", exc)
