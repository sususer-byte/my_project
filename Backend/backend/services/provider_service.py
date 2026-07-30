class BackendProviderService:


    def __init__(self, provider_service):
        self.provider_service = provider_service

    def list(self):
        providers = self.provider_service.list_providers()
        return {
            "providers": providers
        }

    def current(self):
        return {
            "provider":
            self.provider_service.get_current_provider()
        }

    def set_default(self, name):
        self.provider_service.set_current_provider(name)

        return {
            "success": True,
            "provider": name
        }