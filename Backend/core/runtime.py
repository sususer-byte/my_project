import logging
from core.service_registry import ServiceRegistry
from core.bootstrap.bootstrap_manager import bootstrap_all
from core.dependency_container import DependencyContainer

logger = logging.getLogger("furgal.runtime")

class Runtime:
    def __init__(self):
        self.services = ServiceRegistry()
        self.app_lifecycle = None

def create_runtime():
    runtime = Runtime()
    runtime.container = DependencyContainer(runtime.services)
    bootstrap_all(runtime)
 
    return runtime
