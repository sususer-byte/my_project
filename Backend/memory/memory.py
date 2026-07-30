import json
import logging
import os
import threading
from datetime import datetime

logger = logging.getLogger("furgal.memory")


class Memory:
    def __init__(self, path="storage/memory.json"):
        self.path = path
        self.lock = threading.RLock()
        self._ensure_storage_dir()

        if not os.path.exists(self.path):
            self.data = {
                "conversation": [],
                "semantic": [],
                "archived": [],
            }
            self.save()
        else:
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    self.data = json.load(handle)
            except json.JSONDecodeError as exc:
                logger.error("Memory file is corrupted: %s", exc)
                self._backup_corrupt_file()
                self.data = {
                    "conversation": [],
                    "semantic": [],
                    "archived": [],
                }
                self.save()
            if not isinstance(self.data, dict):
                logger.error("Memory file must contain a JSON object; resetting memory store")
                self._backup_corrupt_file()
                self.data = {
                    "conversation": [],
                    "semantic": [],
                    "archived": [],
                }
            if "conversation" not in self.data:
                self.data["conversation"] = []
            if "semantic" not in self.data:
                self.data["semantic"] = []
            if "archived" not in self.data:
                self.data["archived"] = []

            if self.data["semantic"]:
                if isinstance(self.data["semantic"][0], str):
                    logger.warning("Old memory format detected; resetting semantic memory")
                    self.data["semantic"] = []
            self.save()
            logger.info("Loaded memory file: %s", self.path)

    def _ensure_storage_dir(self):
        directory = os.path.dirname(self.path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def save(self):
        with self.lock:
            try:
                tmp_path = f"{self.path}.tmp"
                with open(tmp_path, "w", encoding="utf-8") as handle:
                    json.dump(self.data, handle, ensure_ascii=False, indent=4)
                os.replace(tmp_path, self.path)
            except Exception as exc:
                logger.error("Failed to save memory: %s", exc)

    def _backup_corrupt_file(self):
        try:
            if os.path.exists(self.path):
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                os.replace(self.path, f"{self.path}.corrupt.{timestamp}")
        except Exception as exc:
            logger.error("Failed to back up corrupted memory file: %s", exc)

    def add_message(self, role, content):
        if not role or content is None:
            return
        with self.lock:
            self.data["conversation"].append({
                "role": role,
                "content": content,
            })
            self.save()

    def get_recent_messages(self, limit=10):
        with self.lock:
            return list(self.data["conversation"][-limit:])

    def get_facts(self):
        with self.lock:
            return list(self.data["semantic"])
