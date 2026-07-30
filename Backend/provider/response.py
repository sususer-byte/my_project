from dataclasses import dataclass


@dataclass
class ProviderResponse:

    content: str

    raw: object = None