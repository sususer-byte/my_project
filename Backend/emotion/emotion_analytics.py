import json
import logging
import os
import threading
from collections import deque
from datetime import datetime, timedelta

logger = logging.getLogger("furgal.emotion_analytics")

ANALYTICS_FILE = "storage/emotion_history.json"
MAX_HISTORY_ENTRIES = 500
TREND_WINDOW_DAYS = 14


class EmotionAnalytics:
    TRACKED_EMOTIONS = ("happy", "sad", "angry", "stress", "energy", "curiosity", "trust")

    def __init__(self, file_path=ANALYTICS_FILE):
        self.file_path = file_path
        self._lock = threading.RLock()
        self._ensure_storage_dir()
        self.history = self._load_history()

    def _ensure_storage_dir(self):
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def _load_history(self):
        try:
            if not os.path.exists(self.file_path):
                return []
            with open(self.file_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, list):
                return []
            return data[-MAX_HISTORY_ENTRIES:]
        except Exception as exc:
            logger.error("Failed to load emotion history: %s", exc)
            return []

    def _save_history(self):
        try:
            trimmed = self.history[-MAX_HISTORY_ENTRIES:]
            tmp_path = f"{self.file_path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(trimmed, handle, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.file_path)
            self.history = trimmed
        except Exception as exc:
            logger.error("Failed to save emotion history: %s", exc)

    def record_snapshot(self, snapshot):
        if not snapshot or not isinstance(snapshot, dict):
            return
        state = snapshot.get("state")
        if not isinstance(state, dict):
            return

        entry = {
            "timestamp": snapshot.get("timestamp", datetime.now().isoformat()),
            "session_id": snapshot.get("session_id"),
            "state": {key: float(state.get(key, 0.0)) for key in self.TRACKED_EMOTIONS},
        }

        with self._lock:
            try:
                self.history.append(entry)
                self._save_history()
            except Exception as exc:
                logger.error("Failed to record emotion snapshot: %s", exc)

    def get_recent_entries(self, days=TREND_WINDOW_DAYS):
        cutoff = datetime.now() - timedelta(days=days)
        recent = []
        with self._lock:
            for entry in self.history:
                try:
                    ts = datetime.fromisoformat(entry["timestamp"])
                except (TypeError, ValueError, KeyError):
                    continue
                if ts >= cutoff:
                    recent.append(entry)
        return recent

    def compute_long_term_trends(self, days=TREND_WINDOW_DAYS):
        recent = self.get_recent_entries(days)
        if not recent:
            return {key: 0.5 for key in self.TRACKED_EMOTIONS}

        totals = {key: 0.0 for key in self.TRACKED_EMOTIONS}
        count = len(recent)
        for entry in recent:
            state = entry.get("state", {})
            for key in self.TRACKED_EMOTIONS:
                totals[key] += float(state.get(key, 0.0))

        return {key: round(totals[key] / count, 4) for key in self.TRACKED_EMOTIONS}

    def get_dominant_mood(self, days=TREND_WINDOW_DAYS):
        trends = self.compute_long_term_trends(days)
        mood_scores = {
            "positive": trends.get("happy", 0.0) + trends.get("energy", 0.0) * 0.3,
            "negative": trends.get("sad", 0.0) + trends.get("angry", 0.0) + trends.get("stress", 0.0),
            "curious": trends.get("curiosity", 0.0),
        }
        dominant = max(mood_scores, key=mood_scores.get)
        return {
            "dominant_mood": dominant,
            "scores": mood_scores,
            "trends": trends,
        }

    def get_personality_drift_signals(self, days=TREND_WINDOW_DAYS):
        trends = self.compute_long_term_trends(days)
        return {
            "warmth_signal": (trends.get("happy", 0.5) + trends.get("trust", 0.5)) / 2,
            "humor_signal": max(0.0, trends.get("happy", 0.5) - trends.get("stress", 0.0)),
            "playfulness_signal": (trends.get("curiosity", 0.5) + trends.get("energy", 0.5)) / 2,
            "seriousness_signal": (trends.get("stress", 0.0) + trends.get("sad", 0.0)) / 2,
        }

    def summary_text(self, days=TREND_WINDOW_DAYS):
        mood = self.get_dominant_mood(days)
        trends = mood["trends"]
        return (
            f"Long-term emotional baseline ({days}d): "
            f"dominant={mood['dominant_mood']}, "
            f"happy={trends.get('happy', 0):.2f}, "
            f"sad={trends.get('sad', 0):.2f}, "
            f"stress={trends.get('stress', 0):.2f}"
        )
