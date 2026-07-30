import logging

import numpy as np
from datetime import datetime

logger = logging.getLogger("furgal.vector_memory")


class VectorMemory:
    def __init__(self, memory):
        self.memory = memory
        self.model_name = "all-MiniLM-L6-v2"
        self.model = None

    def _get_model(self):
        if self.model is None:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(self.model_name)
        return self.model

    def embed(self, text):
        try:
            vector = self._get_model().encode(text).tolist()
            return vector
        except Exception as exc:
            logger.error("Embedding failed: %s", exc)
            return [0.0] * 384

    def memory_score(self, similarity, memory):
        importance = memory.get("importance", 0.5)
        confidence = memory.get("confidence", 1.0)
        access = min(memory.get("access_count", 0) / 20, 1)
        score = (
            similarity * 0.55
            + importance * 0.25
            + confidence * 0.15
            + access * 0.05
        )
        return score

    def cosine(self, a, b):
        a = np.array(a)
        b = np.array(b)
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)

    def search_facts(self, query, top_k=3, threshold=0.35):
        q_vec = self.embed(query)
        scores = []
        with self.memory.lock:
            facts = list(self.memory.data["semantic"])
        for fact in facts:
            embedding = fact.get("embedding")
            if not embedding:
                logger.warning("Skipping memory without embedding: %s", fact.get("id"))
                continue
            similarity = self.cosine(q_vec, embedding)
            if similarity < threshold:
                continue
            score = self.memory_score(similarity, fact)
            scores.append((score, similarity, fact))
        scores.sort(reverse=True, key=lambda item: item[0])

        results = []
        with self.memory.lock:
            for score, similarity, fact in scores[:top_k]:
                for stored in self.memory.data["semantic"]:
                    if stored["id"] == fact["id"]:
                        stored["last_used"] = datetime.now().isoformat()
                        stored["access_count"] = stored.get("access_count", 0) + 1
                        stored["last_score"] = round(score, 3)
                        stored["last_similarity"] = round(similarity, 3)
                        results.append({
                            "score": score,
                            "similarity": similarity,
                            "memory": dict(stored),
                        })
                        break
            if results:
                self.memory.save()
        return results
