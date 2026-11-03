from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigurationError(ValueError):
    """Raised when required application configuration is missing or invalid."""


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(f"Missing required environment variable: {name}")
    return value


def _positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be an integer") from error
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True, slots=True)
class AppConfig:
    storage_account_url: str
    storage_container: str
    document_intelligence_endpoint: str
    search_endpoint: str
    search_index_name: str
    openai_endpoint: str
    openai_embedding_deployment: str
    openai_embedding_dimensions: int
    foundry_project_endpoint: str
    foundry_agent_id: str
    foundry_search_connection_name: str | None
    chunk_size: int
    chunk_overlap: int

    @classmethod
    def from_env(cls) -> AppConfig:
        chunk_size = _positive_int("MANUAL_CHUNK_SIZE", 1800)
        chunk_overlap = _positive_int("MANUAL_CHUNK_OVERLAP", 200)
        if chunk_overlap >= chunk_size:
            raise ConfigurationError("MANUAL_CHUNK_OVERLAP must be smaller than MANUAL_CHUNK_SIZE")

        return cls(
            storage_account_url=_required("AZURE_STORAGE_ACCOUNT_URL"),
            storage_container=_required("AZURE_STORAGE_CONTAINER"),
            document_intelligence_endpoint=_required("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
            search_endpoint=_required("AZURE_SEARCH_ENDPOINT"),
            search_index_name=_required("AZURE_SEARCH_INDEX_NAME"),
            openai_endpoint=_required("AZURE_OPENAI_ENDPOINT"),
            openai_embedding_deployment=_required("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
            openai_embedding_dimensions=_positive_int("AZURE_OPENAI_EMBEDDING_DIMENSIONS", 1536),
            foundry_project_endpoint=_required("AZURE_FOUNDRY_PROJECT_ENDPOINT"),
            foundry_agent_id=_required("AZURE_FOUNDRY_AGENT_ID"),
            foundry_search_connection_name=(
                os.getenv("AZURE_FOUNDRY_SEARCH_CONNECTION_NAME", "").strip() or None
            ),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
