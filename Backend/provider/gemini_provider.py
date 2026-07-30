from google import genai
from google.genai import types

import json
import re 

from .base_provider import BaseProvider
from .response import ProviderResponse

class GeminiProvider(BaseProvider):
    def __init__(self, api_key, model):
        self.client = genai.Client(api_key=api_key)
        self.model = model 

    def _clean_json(self, text):
        text = text.strip()
        if "```" in text:
            text = (text.replace("```json", "").replace("```", "").strip())
        match = re.search(r"\{.*\}",text,re.DOTALL,)

        if match:
            return match.group()

        return text

    def _message_to_prompt(self, messages): 
        prompt = ""
        for message in messages:
            role = message["role"]
            content = message["content"]
            prompt += (
                f"{role.upper()}: " 
                f"{content}\n")
        return prompt

    def chat(self, messages, format = None, options = None):
        prompt = self._message_to_prompt(messages)
        config = None
        if options: 
            config = types.GenerateContentConfig(**options)
        response = self.client.models.generate_content(model = self.model, contents = prompt, config = config)
        return ProviderResponse(content = response.text, raw = response)

    def chat_json(self, messages, schema=None, options=None):
        prompt = self._message_to_prompt(messages)
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema, **(options or {}))
        response = self.client.models.generate_content(model=self.model, contents = prompt, config = config)
        content = response.text
        if content.lower().strip() == "null": 
            return None 
        content = self._clean_json(content)
        return json.loads(content)