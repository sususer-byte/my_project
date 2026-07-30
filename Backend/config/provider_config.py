import json
from pathlib import Path


class ProviderConfig:

    def __init__(self):
        base_dir = Path(__file__).resolve().parent
        self.path = base_dir / "provider.json"

        if not self.path.exists():
            self.save(
                {
                    "default_provider": "ollama",
                    "providers": {
                        "ollama": {
                            "enabled": True,
                            "model": "llama3:latest"
                        },
                        "gemini": {
                            "enabled": False,
                            "api_key": "",
                            "model": "gemini-2.5-flash"
                        }
                    }
                }
            )

    def load(self):
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                indent=4
            )

    def get_default_provider(self):
        data = self.load()
        return data["default_provider"]


    def set_default_provider(self, provider):
        data = self.load()
        data["default_provider"] = provider
        self.save(data)


    def get_provider_config(self, provider_name):
        data = self.load()
        return data["providers"][provider_name]


    def set_provider_config(self, provider_name, config):
        data = self.load()
        data["providers"][provider_name] = config
        self.save(data)

    def get_enabled_providers(self):
        data = self.load()

        enabled = []

        for name, config in data["providers"].items():
            if config["enabled"]:
                enabled.append(name)

        return enabled
    
    def set_provider_enabled(self, provider_name, enabled):
        data = self.load()

        data["providers"][provider_name]["enabled"] = enabled

        self.save(data)

    def get_all_provider_configs(self):
        data = self.load()
        return data["providers"]

    def is_provider_enabled(self, provider_name):
        data = self.load()
        return data["providers"][provider_name]["enabled"]

    def list_providers(self):
        data = self.load()
        return list(data["providers"].keys())

    def provider_exists(self, provider_name):
        data = self.load()

        return provider_name in data["providers"]