import logging

logger = logging.getLogger("furgal.services")


class ServiceRegistry:
    def __init__(self):
        self.services = {}

    def register(self, name, service):
        if name in self.services:
            logger.warning("Service %s already registered, replacing", name)
        self.services[name] = service

    def get(self, name):
        if name not in self.services:
            raise KeyError(f"Service '{name}' not found" )
        return self.services[name]

    def has(self, name):
        return name in self.services

    def remove(self, name):
        if name in self.services:
            del self.services[name]


    def list_services(self):
        return list(self.services.keys())