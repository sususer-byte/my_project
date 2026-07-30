import json
import logging
import os
import threading
import uuid
from datetime import datetime

logger = logging.getLogger("furgal.emotion")

DECAY_RATE = 0.02
EMOTION_FILE = "storage/emotion.json"


class Emotion:
    DEFAULT_STATE = {
        "happy": 1.0,
        "angry": 0.0,
        "sad": 0.0,
        "curiosity": 1.0,
        "trust": 1.0,
        "energy": 1.0,
        "stress": 0.0,
    }

    EMOTION_DELTAS = {
        "happy": {"happy": 0.15, "sad": -0.05, "stress": -0.05, "energy": 0.05},
        "sad": {"sad": 0.15, "happy": -0.1, "energy": -0.05, "stress": 0.05},
        "angry": {"angry": 0.15, "happy": -0.05, "stress": 0.1, "trust": -0.05},
        "neutral": {"stress": -0.02},
    }

    def __init__(self, file_path=EMOTION_FILE):
        self.file_path = file_path
        self._lock = threading.RLock()
        self._ensure_storage_dir()
        self.data = self._load_or_create()
        self.session_id = str(uuid.uuid4())

    def _ensure_storage_dir(self):
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def _load_or_create(self):
        try:
            if not os.path.exists(self.file_path):
                state = dict(self.DEFAULT_STATE)
                self._write_file(state)
                return state
            with open(self.file_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if not isinstance(loaded, dict):
                raise ValueError("Emotion file must contain a JSON object")
            merged = dict(self.DEFAULT_STATE)
            for key, value in loaded.items():
                if key in merged:
                    try:
                        merged[key] = self._clamp(value)
                    except (TypeError, ValueError):
                        logger.warning("Invalid emotion value for %s, using default", key)
            return merged
        except Exception as exc:
            logger.error("Failed to load emotion state: %s", exc)
            return dict(self.DEFAULT_STATE)

    def _write_file(self, state):
        tmp_path = f"{self.file_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=4)
        os.replace(tmp_path, self.file_path)

    def _clamp(self, value):
        return max(0.0, min(1.0, float(value)))

    def save(self):
        with self._lock:
            try:
                self._write_file(self.data)
            except Exception as exc:
                logger.error("Failed to save emotion state: %s", exc)

    def state(self):
        with self._lock:
            return dict(self.data)

    def decay(self, rate=DECAY_RATE):
        with self._lock:
            try:
                for key in self.data:
                    current = float(self.data[key])
                    if current > 0.5:
                        self.data[key] = self._clamp(current - rate)
                    elif current < 0.5:
                        self.data[key] = self._clamp(current + rate * 0.5)
                self.save()
            except Exception as exc:
                logger.error("Emotion decay failed: %s", exc)

    def update(self, analysis):
        if not analysis or not isinstance(analysis, dict):
            return
        emotion = analysis.get("emotion")
        intensity = analysis.get("intensity")
        if emotion not in self.EMOTION_DELTAS:
            return
        try:
            intensity = float(intensity)
        except (TypeError, ValueError):
            return
        intensity = self._clamp(intensity)

        with self._lock:
            try:
                deltas = self.EMOTION_DELTAS[emotion]
                for trait, delta in deltas.items():
                    if trait in self.data:
                        self.data[trait] = self._clamp(
                            self.data[trait] + delta * intensity
                        )
                if emotion == "happy":
                    self.data["trust"] = self._clamp(self.data["trust"] + 0.02 * intensity)
                elif emotion == "sad":
                    self.data["curiosity"] = self._clamp(
                        self.data["curiosity"] + 0.03 * intensity
                    )
                self.save()
            except Exception as exc:
                logger.error("Emotion update failed: %s", exc)

    def snapshot_for_analytics(self):
        with self._lock:
            return {
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "state": dict(self.data),
            }
