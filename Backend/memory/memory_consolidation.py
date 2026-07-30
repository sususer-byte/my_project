import logging

logger = logging.getLogger("furgal.memory_consolidation")


class MemoryConsolidation:
    def __init__(self, memory, vector_memory):
        self.memory = memory
        self.vector_memory = vector_memory

    def find_similarity(self, new_memory, threshold=0.85):
        results = []
        new_embedding = self.vector_memory.embed(new_memory["text"])
        with self.memory.lock:
            semantic = list(self.memory.data["semantic"])
        for memory in semantic:
            if memory["id"] == new_memory["id"]:
                continue
            memories_similarity = self.vector_memory.cosine(new_embedding, memory["embedding"])
            if memories_similarity >= threshold:
                results.append({
                    "memory": memory,
                    "similarity": memories_similarity,
                })
        return results

    def consolidate(self, new_memory):
        similar_memories = self.find_similarity(new_memory)
        if len(similar_memories) < 2:
            return None
        memories_to_merge = [new_memory]
        for item in similar_memories:
            memories_to_merge.append(item["memory"])
        return memories_to_merge

    def is_duplicate(self, text):
        text = text.lower().strip()
        with self.memory.lock:
            for memory in self.memory.data["semantic"]:
                if memory["text"].strip().lower() == text:
                    return True
        return False

    def execute_merge(self, brain, memory_manager, memories_to_merge):
        merge_text = brain.merge_memories(memories_to_merge)
        if not merge_text:
            return None
        best = max(memories_to_merge, key=lambda item: item.get("importance", 0.0))
        importance = max(item.get("importance", 0.0) for item in memories_to_merge)
        confidence = max(item.get("confidence", 0.0) for item in memories_to_merge)
        category = best.get("category", "other")
        old_ids = [item["id"] for item in memories_to_merge if "id" in item]
        return memory_manager.replace_with_merged(
            old_ids=old_ids,
            merged_text=merge_text,
            category=category,
            importance=importance,
            confidence=confidence,
        )

    def consolidate_and_merge(self, brain, memory_manager, new_memory):
        if not new_memory or not isinstance(new_memory, dict):
            return False
        cluster = self.consolidate(new_memory)
        if not cluster:
            return False
        result = self.execute_merge(brain, memory_manager, cluster)
        return bool(result)
