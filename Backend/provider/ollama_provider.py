from ollama import chat
from .response import ProviderResponse
from .base_provider import BaseProvider
import re
import json


class OllamaProvider(BaseProvider):

    def __init__(self,model):
        self.model = model

    def chat(self, messages, format = None, options = None) -> ProviderResponse: 
        response = chat(model = self.model, messages= messages, format= format, options=options)
        return ProviderResponse(content = response["message"]["content"], raw = response)

    def _clean_json(self, text):
        text = text.strip()
        if "```" in text:
            text = (text.replace("```json", "").replace("```", "").strip())
        match =re.search(r"\{.*\}",text, re.DOTALL)
        if match:
            return match.group()    
        return text

    def chat_json(self, messages, schema = None, options = None):
        response = chat(model = self.model, messages= messages, format = schema, options= options)
        content = response["message"]["content"]
        if content.lower().strip() == "null":
            return None
        content = self._clean_json(content)
        return json.loads(content)