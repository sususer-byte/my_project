class DependencyContainer:

    def __init__(self, services):
        super().__setattr__("services", services)


    def get(self, name):
        return self.services.get(name)


    def has(self, name):
        return self.services.has(name)

    def __getattr__(self, name):
        if self.services.has(name):
            return self.services.get(name)
        raise AttributeError(
            f"{type(self).__name__!r} object has no attribute {name!r}"
        )

    def __setattr__(self, name, value):
        if name == "services": 
            super().__setattr__(name,value)
            return 
        self.services.register(name,value)

    def __contains__(self, name):
        return self.services.has(name)

    def keys(self):
        return self.services.list_services()