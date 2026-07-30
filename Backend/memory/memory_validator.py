class MemoryValidator:

    REQUIRED_FIELDS = ["text", "category", "importance", "confidence"]
    VALID_CATEGORIES = [
        "identity",
        "interest",
        "skill", 
        "project", 
        "preference", 
        "goal", 
        "relationship",
        "other",
    ]

    def validate(self, memory):
        if not memory:
            return False 
        
        for key in self.REQUIRED_FIELDS:
            if key not in memory:
                return False 
        
        if not isinstance(memory["text"], str) or not memory["text"].strip():
            return False 
        if memory["category"] not in self.VALID_CATEGORIES:
            return False
        
        try:
            importance = float(memory["importance"])
            confidence = float(memory["confidence"])

        except(TypeError, ValueError):
            return False
        
        if not (0.0 < importance <= 1.0):
            return False 
        if not (0.0 < confidence <= 1.0):
            return False 
        if confidence < 0.7 :
            return False 
        
        return True