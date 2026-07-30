import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger("furgal.memory_workers")


class MemoryBackgroundWorker:
    def __init__(
        self,
        lifecycle,
        consolidation=None,
        brain=None,
        memory_manager=None,
        interval_seconds: int = 60,
        on_cycle_complete: Optional[Callable] = None,
    ):
        self.lifecycle = lifecycle
        self.consolidation = consolidation
        self.brain = brain
        self.memory_manager = memory_manager
        self.interval_seconds = max(10, int(interval_seconds))
        self.on_cycle_complete = on_cycle_complete
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    @property
    def is_running(self):
        return self._running and self._thread is not None and self._thread.is_alive()

    def _run_importance_recalculation(self):
        if self.memory_manager is None:
            return
        try:
            lock = getattr(self.memory_manager.memory, "lock", None)
            if lock:
                with lock:
                    self._recalculate_importance_unlocked()
            else:
                self._recalculate_importance_unlocked()
        except Exception as exc:
            logger.error("Importance recalculation failed: %s", exc)

    def _recalculate_importance_unlocked(self):
        for memory in list(self.memory_manager.memory.data.get("semantic", [])):
            access = float(memory.get("access_count", 0))
            base = float(memory.get("importance", 0.5))
            boost = min(0.1, access * 0.01)
            if boost > 0:
                new_importance = min(1.0, base + boost)
                if new_importance != base:
                    self.memory_manager.update_fields(memory["id"], importance=new_importance, _skip_lock=True)

    def _run_auto_merge(self):
        if not self.consolidation or not self.brain or not self.memory_manager:
            return
        try:
            lock = getattr(self.memory_manager.memory, "lock", None)
            if lock:
                with lock:
                    semantic = list(self.memory_manager.memory.data.get("semantic", []))
            else:
                semantic = list(self.memory_manager.memory.data.get("semantic", []))
            for memory in semantic:
                cluster = self.consolidation.consolidate(memory)
                if not cluster:
                    continue
                self.consolidation.execute_merge(self.brain, self.memory_manager, cluster)
        except Exception as exc:
            logger.error("Automatic merge worker failed: %s", exc)

    def _run_lifecycle(self):
        try:
            lock = getattr(self.memory_manager.memory, "lock", None) if self.memory_manager else None
            if lock:
                with lock:
                    result = self.lifecycle.run_cycle()
            else:
                result = self.lifecycle.run_cycle()
            logger.info("Background lifecycle cycle: %s", result)
            if self.on_cycle_complete:
                self.on_cycle_complete(result)
            return result
        except Exception as exc:
            logger.error("Background lifecycle failed: %s", exc)
            return None

    def _worker_loop(self):
        logger.info("Memory background worker started (interval=%ss)", self.interval_seconds)
        while not self._stop_event.is_set():
            self._run_lifecycle()
            self._run_importance_recalculation()
            self._run_auto_merge()
            self._stop_event.wait(self.interval_seconds)
        logger.info("Memory background worker stopped")

    def start(self):
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._worker_loop,
            name="furgal-memory-worker",
            daemon=True,
        )
        self._thread.start()
        self._running = True

    def stop(self, timeout: float = 5.0):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        self._running = False

    def run_once(self):
        lifecycle_result = self._run_lifecycle()
        self._run_importance_recalculation()
        self._run_auto_merge()
        return lifecycle_result
