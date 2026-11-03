import pytest

from manual_ingestion.config import AppConfig, ConfigurationError

REQUIRED = {
    "AZURE_STORAGE_ACCOUNT_URL": "https://storage.blob.core.windows.net",
    "AZURE_STORAGE_CONTAINER": "manuals",
    "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT": "https://doc.example",
    "AZURE_SEARCH_ENDPOINT": "https://search.example",
    "AZURE_SEARCH_INDEX_NAME": "manuals",
    "AZURE_OPENAI_ENDPOINT": "https://openai.example",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "embedding",
    "AZURE_FOUNDRY_PROJECT_ENDPOINT": "https://foundry.example/api/projects/project",
    "AZURE_FOUNDRY_AGENT_ID": "agent",
}


def test_config_loads_required_values(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in REQUIRED.items():
        monkeypatch.setenv(name, value)

    config = AppConfig.from_env()

    assert config.storage_container == "manuals"
    assert config.openai_embedding_dimensions == 1536


def test_config_rejects_missing_value(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in REQUIRED.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("AZURE_SEARCH_ENDPOINT")

    with pytest.raises(ConfigurationError, match="AZURE_SEARCH_ENDPOINT"):
        AppConfig.from_env()