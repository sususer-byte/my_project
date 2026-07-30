from .base_provider import BaseProvider
import logging 


logger = logging.getLogger("furgal.provider")

# [MODIFICATION]: Add custom exception class for provider fallback errors
class ProviderFallbackError(RuntimeError):
    """Exception raised when all providers fail during fallback"""
    pass

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
        # [MODIFICATION]: Enhanced provider switching with validation
        if name not in self.providers:
            raise ValueError(f"Provider '{name}' does not exist")
        self.default_provider = name
        self.runtime_provider = name
        logger.info("Switched to provider: %s", name)

    def set_default_provider(self, name: str):
        # [MODIFICATION]: Separate method for setting default provider
        if name not in self.providers:
            raise ValueError(f"Provider '{name}' does not exist")
        self.default_provider = name
        logger.info("Set default provider to: %s", name)

    def get_current_provider_info(self):
        # [MODIFICATION]: Get detailed information about current provider
        return {
            "current_provider": self.runtime_provider,
            "default_provider": self.default_provider,
            "available_providers": self.list_enabled_providers(),
            "fallback_order": self.get_fallback_providers()
        }

    def get_default_provider_name(self): 
        return self.default_provider

    def get_runtime_provider_name(self):
        return self.runtime_provider

    def list_provider(self):
        return self.provider_order.copy()

    def chat(self, messages, format = None, options = None):
        # [FIX]: Fix error swallowing in fallback loop - log and handle exceptions properly
        last_exception = None 
        attempted_providers = []
        
        for provider_name in self.get_fallback_providers():
            try:
                response = self._try_provider_chat(provider_name, messages, format, options)
                self.runtime_provider = provider_name
                logger.info("Provider %s succeeded after %d attempts", provider_name, len(attempted_providers) + 1)
                return response
            except Exception as exc:
                logger.warning("Provider %s failed: %s", provider_name, exc)
                attempted_providers.append(provider_name)
                last_exception = exc
                # [FIX]: Continue to next provider instead of swallowing the error
                continue
        
        # [FIX]: Provide detailed error information including which providers were tried
        error_msg = f"All providers failed after attempting: {', '.join(attempted_providers)}"
        if last_exception:
            logger.error("Final provider failure details: %s", str(last_exception))
        raise ProviderFallbackError(error_msg) from last_exception
    
    def chat_json(self, messages, schema= None, options = None):
        # [FIX]: Fix error swallowing in fallback loop for JSON chat as well
        last_exception = None 
        attempted_providers = []
        
        for provider_name in self.get_fallback_providers():
            try: 
                response = self._try_provider_chat_json(provider_name, messages, schema, options)
                self.runtime_provider = provider_name
                logger.info("Provider %s succeeded for JSON chat after %d attempts", provider_name, len(attempted_providers) + 1)
                return response
            except Exception as exc: 
                logger.warning("Provider %s failed for JSON chat: %s", provider_name, exc)
                attempted_providers.append(provider_name)
                last_exception = exc
                continue
        
        error_msg = f"All providers failed for JSON chat after attempting: {', '.join(attempted_providers)}"
        if last_exception:
            logger.error("Final JSON chat provider failure details: %s", str(last_exception))
        raise ProviderFallbackError(error_msg) from last_exception
    
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