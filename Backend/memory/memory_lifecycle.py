import logging
from datetime import datetime

logger = logging.getLogger("furgal.memory_lifecycle")


class MemoryLifecycle:
    PERSISTENT_CATEGORIES = {"identity", "goal"}

    def __init__(
        self,
        memory_manager,
        decay_rate=0.05,
        stale_days=30,
        forget_threshold=0.15,
        reinforce_step=0.02,
    ):
        self.memory_manager = memory_manager
        self.decay_rate = decay_rate
        self.stale_days = stale_days
        self.forget_threshold = forget_threshold
        self.reinforce_step = reinforce_step

    def _days_since(self, iso_timestamp):
        try:
            last = datetime.fromisoformat(iso_timestamp)
        except (TypeError, ValueError):
            return self.stale_days + 1
        return (datetime.now() - last).days

    def decay_importance(self):
        with self.memory_manager.memory.lock:
            for memory in list(self.memory_manager.memory.data["semantic"]):
                if memory.get("category") in self.PERSISTENT_CATEGORIES:
                    continue
                last_used = memory.get("last_used", memory.get("created"))
                if self._days_since(last_used) < self.stale_days:
                    continue
                new_importance = max(0.0, memory.get("importance", 0.5) - self.decay_rate)
                self.memory_manager.update_fields(memory["id"], importance=new_importance, _skip_lock=True)
                logger.info("Decay importance of %s --> %.2f", memory["id"], new_importance)

    def reinforce_confidence(self):
        with self.memory_manager.memory.lock:
            for memory in list(self.memory_manager.memory.data["semantic"]):
                if memory.get("access_count", 0) >= 3 and memory.get("confidence", 1.0) < 1.0:
                    new_confidence = min(1.0, memory["confidence"] + self.reinforce_step)
                    self.memory_manager.update_fields(
                        memory["id"], confidence=new_confidence, _skip_lock=True
                    )

    def forget(self):
        with self.memory_manager.memory.lock:
            to_forget = [
                item["id"]
                for item in self.memory_manager.memory.data["semantic"]
                if item.get("category") not in self.PERSISTENT_CATEGORIES
                and item.get("importance", 0.0) < self.forget_threshold
                and item.get("access_count", 0) == 0
            ]
            for memory_id in to_forget:
                self.memory_manager.remove_memory(memory_id, archive=True, _skip_lock=True)
        if to_forget:
            logger.info("Archived %d stale memories", len(to_forget))
        return len(to_forget)

    def run_cycle(self):
        self.decay_importance()
        self.reinforce_confidence()
        forgotten = self.forget()
        return {"forgotten": forgotten}
