from provider.ollama_provider import OllamaProvider
from provider.gemini_provider import GeminiProvider
from provider.provider_manager import ProviderManager

class ProviderFactory:

    PROVIDERS = {
        "ollama": OllamaProvider,
        "gemini": GeminiProvider,
    }

    @classmethod
    def create_provider(cls, provider_name, config):

        if provider_name not in cls.PROVIDERS:
            raise ValueError(
                f"Unknown provider: {provider_name}"
            )

        provider_class = cls.PROVIDERS[provider_name]

        return provider_class(**config)

    @classmethod
    def create_manager(cls, provider_config):
        manager = ProviderManager()
        default_provider = provider_config.get_default_provider()
        enabled_providers = provider_config.get_enabled_providers()
        for provider_name in enabled_providers:
            config = provider_config.get_provider_config(provider_name)
            provider_config ={
                key: value 
                for key, value in config.items()
                if key != "enabled"
            }
            provider = cls.create_provider(
                provider_name, provider_config
            )
            manager.register_provider(
                provider_name,
                provider
            )

        manager.set_provider(default_provider)

        return manager