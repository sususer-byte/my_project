import logging
import re
import uuid
from datetime import datetime

logger = logging.getLogger("furgal.memory_manager")


class MemoryManager:
    DUPLICATE_SIMILARITY_THRESHOLD = 0.92

    def __init__(self, memory, vector_memory):
        self.memory = memory
        self.vector_memory = vector_memory
        self._repair_semantic_memories()

    def _repair_semantic_memories(self):
        changed = False
        with self.memory.lock:
            for item in self.memory.data["semantic"]:
                normalized = self._normalize_memory_text(
                    item.get("text", ""),
                    item.get("category", "other"),
                )
                if normalized and normalized != item.get("text"):
                    item["text"] = normalized
                    changed = True
            if changed:
                self.memory.save()

    def _normalize_memory_text(self, text, category):
        if not text or not str(text).strip():
            return ""
        text = str(text).strip()
        if category == "identity":
            lower = text.lower()
            if "name" not in lower and "user" not in lower:
                return f"The user's name is {text}"
        return text

    def _memory_matches_query_intent(self, query, memory):
        query = (query or "").lower()
        category = memory.get("category", "other")
        text = memory.get("text", "").lower()

        asks_identity = any(
            phrase in query
            for phrase in (
                "my name",
                "who am i",
                "remember me",
                "know me",
                "my identity",
            )
        )
        if asks_identity and category == "identity":
            return True

        asks_preference = any(
            word in query
            for word in (
                "favorite",
                "favourite",
                "what do i like",
                "what i like",
                "do i like",
                "do i love",
                "i love",
                "i like",
            )
        )
        if asks_preference and category in ("interest", "preference"):
            return True

        query_words = {
            word
            for word in re.findall(r"[a-z0-9]+", query)
            if len(word) > 2 and word not in {"you", "know", "what", "does", "remember"}
        }
        if query_words and query_words.intersection(re.findall(r"[a-z0-9]+", text)):
            return True

        return False

    def exists(self, text):
        with self.memory.lock:
            for item in self.memory.data["semantic"]:
                if item["text"] == text:
                    return True
        return False

    def is_semantic_duplicate(self, text):
        with self.memory.lock:
            if not self.memory.data["semantic"]:
                return False
            candidate = self.vector_memory.embed(text)
            for item in self.memory.data["semantic"]:
                similarity = self.vector_memory.cosine(candidate, item["embedding"])
                if similarity >= self.DUPLICATE_SIMILARITY_THRESHOLD:
                    return True
        return False

    def _calculate_dynamic_relevance_score(self, memory, query):
        # [MODIFICATION]: Dynamic relevance scoring algorithm
        category = memory.get("category", "other")
        importance = memory.get("importance", 0.5)
        confidence = memory.get("confidence", 1.0)
        access_count = memory.get("access_count", 0)
        
        # Base score based on category
        category_weights = {
            "identity": 0.9,
            "goal": 0.85,
            "interest": 0.75,
            "preference": 0.7,
            "skill": 0.65,
            "project": 0.6,
            "relationship": 0.55,
            "other": 0.5
        }
        
        base_score = category_weights.get(category, 0.5)
        
        # Adjust based on memory characteristics
        score = (
            base_score * 0.6 +  # Category importance
            importance * 0.2 +   # Memory importance
            confidence * 0.1 +   # Confidence in memory
            min(access_count / 10, 0.1)  # Usage frequency (capped at 0.1)
        )
        
        # Query-specific adjustments
        query_lower = (query or "").lower()
        memory_text = (memory.get("text", "") or "").lower()
        
        # Boost score if query contains key terms from memory
        if memory_text and any(term in query_lower for term in memory_text.split()[:3]):
            score = min(1.0, score + 0.1)
            
        return max(0.3, min(0.99, score))  # Clamp between 0.3 and 0.99

    def add_memory(self, text, category="unknown", importance=0.5, confidence=1.0):
        text = self._normalize_memory_text(text, category)
        if not text or not str(text).strip():
            return None
        try:
            importance = max(0.0, min(1.0, float(importance)))
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            return None
        if confidence < 0.7:
            return None
        if self.exists(text):
            return None
        if self.is_semantic_duplicate(text):
            return None

        now = datetime.now().isoformat()
        memory = {
            "id": str(uuid.uuid4()),
            "text": text,
            "category": category,
            "importance": importance,
            "confidence": confidence,
            "created": now,
            "last_used": now,
            "access_count": 0,
            "embedding": self.vector_memory.embed(text),
        }
        with self.memory.lock:
            self.memory.data["semantic"].append(memory)
            self.memory.save()
        return memory

    def retrieve_memory(self, query):
        # [FIX]: Replace hardcoded relevance scores with dynamic scoring algorithm
        results_by_id = {}

        with self.memory.lock:
            for memory in self.memory.data["semantic"]:
                memory_id = memory.get("id")
                if not memory_id or memory_id in results_by_id:
                    continue
                if self._memory_matches_query_intent(query, memory):
                    stored = dict(memory)
                    # [MODIFICATION]: Dynamic relevance scoring based on memory characteristics
                    score = self._calculate_dynamic_relevance_score(stored, query)
                    stored["last_used"] = datetime.now().isoformat()
                    stored["access_count"] = stored.get("access_count", 0) + 1
                    stored["last_score"] = round(score, 3)
                    results_by_id[memory_id] = {
                        "score": score,
                        "similarity": None,
                        "memory": stored,
                    }
                    memory["last_used"] = stored["last_used"]
                    memory["access_count"] = stored["access_count"]
                    memory["last_score"] = stored["last_score"]
            if results_by_id:
                self.memory.save()

        if results_by_id:
            return sorted(
                results_by_id.values(),
                reverse=True,
                key=lambda item: item.get("score", 0.0),
            )[:5]

        vector_results = self.vector_memory.search_facts(query)
        results_by_id = {
            item["memory"]["id"]: item
            for item in vector_results
            if item.get("memory", {}).get("id")
        }

        return sorted(
            results_by_id.values(),
            reverse=True,
            key=lambda item: item.get("score", 0.0),
        )[:5]

    def get_by_id(self, memory_id):
        with self.memory.lock:
            for item in self.memory.data["semantic"]:
                if item["id"] == memory_id:
                    return dict(item)
        return None

    def remove_memory(self, memory_id, archive=True, _skip_lock=False):
        def _remove():
            target = None
            for item in self.memory.data["semantic"]:
                if item["id"] == memory_id:
                    target = item
                    break
            if not target:
                return False
            self.memory.data["semantic"] = [
                item for item in self.memory.data["semantic"] if item["id"] != memory_id
            ]
            if archive:
                archived = dict(target)
                archived["archived_at"] = datetime.now().isoformat()
                self.memory.data["archived"].append(archived)
            self.memory.save()
            return True

        if _skip_lock:
            return _remove()
        with self.memory.lock:
            return _remove()

    def update_fields(self, memory_id, _skip_lock=False, **fields):
        def _update():
            for item in self.memory.data["semantic"]:
                if item["id"] == memory_id:
                    item.update(fields)
                    self.memory.save()
                    return True
            return False

        if _skip_lock:
            return _update()
        with self.memory.lock:
            return _update()

    def replace_with_merged(self, old_ids, merged_text, category, importance, confidence):
        if not merged_text or not str(merged_text).strip():
            return None
        with self.memory.lock:
            for memory_id in old_ids:
                self.remove_memory(memory_id, archive=True, _skip_lock=True)
        return self.add_memory(
            text=merged_text,
            category=category,
            importance=importance,
            confidence=confidence,
        )
