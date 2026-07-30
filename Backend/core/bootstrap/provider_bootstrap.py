from config.provider_config import ProviderConfig
from provider.provider_factory import ProviderFactory

def bootstrap_provider(runtime):
    provider_config = ProviderConfig()
    runtime.container.provider_config = provider_config

    provider_manager = ProviderFactory.create_manager(provider_config)
    runtime.container.provider_manager = provider_manager