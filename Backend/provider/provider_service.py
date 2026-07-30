from config.provider_config import ProviderConfig
from provider.provider_factory import ProviderFactory

class ProviderService:
    def __init__(self):
        self.config = ProviderConfig()
        self.manager = ProviderFactory.create_manager(self.config.get_provider(),self.config.get_provider_config())
        for provider in self.manager.list_provider():
            if self.config.is_provider_enabled(provider):
                self.manager.enable_provider(provider)
            else:
                self.manager.disable_provider(provider)

    def get_current_provider(self):
        return self.manager.get_default_provider_name()

    def set_current_provider(self, provider_name):
        self.manager.set_provider(provider_name)
        self.config.set_default_provider(provider_name)

    def list_providers(self):
        return self.manager.list_provider()

    def provider_exists(self, provider_name):
        return self.manager.has_provider(provider_name)

    def enable_provider(self, provider_name):
        self.manager.enable_provider(provider_name)
        self.config.set_provider_enabled(provider_name, True)

    def disable_provider(self, provider_name):
        self.manager.disable_provider(provider_name)
        self.config.set_provider_enabled(provider_name, False)

    def is_provider_enabled(self, provider_name):
        return self.manager.is_provider_enabled(provider_name)

    def list_enabled_providers(self):
        return self.manager.list_enabled_providers()
