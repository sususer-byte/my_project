from .base_provider import BaseProvider
import logging 


logger = logging.getLogger("furgal.provider")

class ProviderManager:

    def __init__(self):
        self.providers = {}
        self.default_provider = None 
        self.runtime_provider = None
        self.provider_order = []
        self.enabled_providers = set()

    def register_provider(self, name:str, provider : BaseProvider):
        self.providers[name] = provider
        self.enabled_providers.add(name)
        if name not in self.provider_order: 
            self.provider_order.append(name)

        if self.default_provider is None:
            self.default_provider = name
        if self.runtime_provider is None:
            self.runtime_provider = name

    def get_provider(self):
        if self.runtime_provider is None:
            raise RuntimeError("No provider has been registered")
        return self.providers[self.runtime_provider]

    def set_provider(self, name:str):
        if name not in self.providers:
            raise ValueError(f"Provider '{name}' does not exist")
        self.default_provider = name
        self.runtime_provider = name

    def get_default_provider_name(self): 
        return self.default_provider

    def get_runtime_provider_name(self):
        return self.runtime_provider

    def list_provider(self):
        return self.provider_order.copy()

    def chat(self, messages, format = None, options = None):
        last_exception = None 
        for provider_name in self.get_fallback_providers():
            try:
                response = self._try_provider_chat(provider_name, messages, format, options)
                self.runtime_provider = provider_name
                return response
            except Exception as exc :
                logger.warning("Provider %s failed: %s", provider_name, exc,)
                last_exception =exc
        raise RuntimeError("All providers failed.") from last_exception
    
    def chat_json(self, messages, schema= None, options = None):
        last_exception = None
        for provider_name in self.get_fallback_providers():
            try: 
                response = self._try_provider_chat_json(provider_name, messages, schema, options)
                self.runtime_provider = provider_name
                return response
            except Exception as exc: 
                logger.warning("Provider %s failed: %s", provider_name, exc)
                last_exception = exc
        raise RuntimeError("All providers failed.") from last_exception
    
    def has_provider(self, name: str):
        return name in self.providers
    
    def get_provider_by_name(self, name: str):
        return self.providers[name]
    
    def unregister_provider(self, name: str):
        if name not in self.providers:
            return 
        del self.providers[name]
        self.enabled_providers.discard(name)
        if name in self.provider_order:
            self.provider_order.remove(name)
        if self.default_provider == name:
            self.default_provider = (self.default_provider[0] if self.provider_order else None)
        if self.runtime_provider == name:
            self.runtime_provider = (self.runtime_provider[0] if self.provider_order else None)
        

    def provider_count(self):
        return len(self.providers)

    def get_provider_order(self):
        return self.provider_order.copy()
    
    def get_fallback_providers(self):

        if self.default_provider is None:
            return []

        index = self.provider_order.index(self.default_provider)
        ordered = (
            self.provider_order[index:]
            + self.provider_order[:index]
        )

        return [
            provider
            for provider in ordered
            if provider in self.enabled_providers
]

    def _try_provider_chat(self, provider_name, messages, format = None, options = None): 
        provider = self.get_provider_by_name(provider_name)
        return provider.chat(messages = messages, format = format, options = options)

    def _try_provider_chat_json(self, provider_name, messages, schema = None, options=None): 
        provider = self.get_provider_by_name(provider_name)
        return provider.chat_json(messages = messages, schema = schema, options = options)
    
    def enable_provider(self, name: str):
        if name not in self.providers:
            raise ValueError(f"Provider '{name}' does not exist")
        self.enabled_providers.add(name)

    def disable_provider(self, name: str):
        self.enabled_providers.discard(name)

    def is_provider_enabled(self, name: str):
        return name in self.enabled_providers
    
    def list_enabled_providers(self):
        return [provider for provider in self.provider_order if provider in self.enabled_providers]