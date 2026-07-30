from provider.ollama_provider import OllamaProvider
from provider.gemini_provider import GeminiProvider
from provider.provider_manager import ProviderManager

class ProviderFactory:

    # [MODIFICATION]: Enhanced provider registry with better error handling
    PROVIDERS = {
        "ollama": OllamaProvider,
        "gemini": GeminiProvider,
        # [MODIFICATION]: Add placeholder for additional providers
        # "openai": OpenAIProvider,
        # "claude": ClaudeProvider,
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
        # [MODIFICATION]: Enhanced manager creation with better error handling and validation
        manager = ProviderManager()
        default_provider = provider_config.get_default_provider()
        enabled_providers = provider_config.get_enabled_providers()
        
        if not enabled_providers:
            logger.warning("No enabled providers found, falling back to default")
            enabled_providers = [default_provider]
        
        successfully_registered = []
        
        for provider_name in enabled_providers:
            try:
                config = provider_config.get_provider_config(provider_name)
                # [MODIFICATION]: Clean config by removing non-provider parameters
                provider_config_dict = {
                    key: value 
                    for key, value in config.items()
                    if key != "enabled"
                }
                
                # [MODIFICATION]: Validate required configuration
                if not provider_config_dict:
                    logger.warning("Empty configuration for provider %s, skipping", provider_name)
                    continue
                    
                provider = cls.create_provider(provider_name, provider_config_dict)
                manager.register_provider(provider_name, provider)
                successfully_registered.append(provider_name)
                logger.info("Successfully registered provider: %s", provider_name)
                
            except Exception as exc:
                logger.error("Failed to register provider %s: %s", provider_name, exc)
                continue
        
        # [MODIFICATION]: Ensure at least one provider is registered
        if not successfully_registered:
            raise RuntimeError(f"No providers could be registered. Check configuration for: {enabled_providers}")
        
        # [MODIFICATION]: Set default provider with validation
        if default_provider not in successfully_registered:
            logger.warning("Default provider %s not available, using first available: %s", 
                          default_provider, successfully_registered[0])
            default_provider = successfully_registered[0]
        
        manager.set_provider(default_provider)
        logger.info("Provider manager initialized with default: %s, available: %s", 
                   default_provider, successfully_registered)

        return manager