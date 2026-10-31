from datetime import date
from typing import TypedDict


class PolicyDocument(TypedDict):
    document_id: str
    path: str
    country: str
    language: str
    allowed_roles: list[str]
    version: str
    effective_from: date
    effective_to: date | None
    status: str
