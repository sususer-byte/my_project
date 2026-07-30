from abc import ABC, abstractmethod
from .response import ProviderResponse


class BaseProvider(ABC):

    @abstractmethod
    def chat(self, messages, format=None, options=None) -> ProviderResponse:
        pass

    @abstractmethod
    def chat_json(self, messages, schema = None, options = None) -> dict: 
        pass