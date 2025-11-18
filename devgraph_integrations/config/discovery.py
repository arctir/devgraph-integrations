from uuid import UUID

from pydantic import Field

from .base import SensitiveBaseModel


class MoleculeConfig(SensitiveBaseModel):
    name: str
    type: str
    every: int = 60
    config: dict = {}


class DiscoveryConfig(SensitiveBaseModel):
    api_base_url: str = "http://localhost:8000"
    environment: UUID
    opaque_token: str
    molecules: list[MoleculeConfig] = Field(
        default=[], description="Molecule configurations for discovery"
    )
