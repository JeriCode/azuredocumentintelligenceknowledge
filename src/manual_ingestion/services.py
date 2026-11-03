from __future__ import annotations

from dataclasses import dataclass

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI

from manual_ingestion.adapters.blob_storage import AzureBlobStorage
from manual_ingestion.adapters.document_intelligence import AzureDocumentIntelligence
from manual_ingestion.adapters.embeddings import AzureOpenAIEmbeddings
from manual_ingestion.adapters.foundry_knowledge_source import MicrosoftFoundryKnowledgeSource
from manual_ingestion.adapters.search_index import AzureSearchIndex
from manual_ingestion.config import AppConfig
from manual_ingestion.ingestion import IngestionValidationService, ManualIngestionService


@dataclass(slots=True)
class ServiceContainer:
    ingestion: ManualIngestionService
    validation: IngestionValidationService


def build_services(config: AppConfig) -> ServiceContainer:
    credential = DefaultAzureCredential()
    blob = AzureBlobStorage(
        BlobServiceClient(account_url=config.storage_account_url, credential=credential),
        config.storage_container,
    )
    document_intelligence = AzureDocumentIntelligence(
        DocumentIntelligenceClient(
            endpoint=config.document_intelligence_endpoint,
            credential=credential,
        )
    )
    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default",
    )
    embeddings = AzureOpenAIEmbeddings(
        AzureOpenAI(
            azure_endpoint=config.openai_endpoint,
            azure_ad_token_provider=token_provider,
            api_version="2024-10-21",
        ),
        config.openai_embedding_deployment,
        config.openai_embedding_dimensions,
    )
    index_client = SearchIndexClient(endpoint=config.search_endpoint, credential=credential)
    search_client = SearchClient(
        endpoint=config.search_endpoint,
        index_name=config.search_index_name,
        credential=credential,
    )
    search = AzureSearchIndex(
        index_client,
        search_client,
        config.search_index_name,
        config.openai_embedding_dimensions,
    )
    foundry = MicrosoftFoundryKnowledgeSource(
        AIProjectClient(endpoint=config.foundry_project_endpoint, credential=credential),
        config.foundry_agent_id,
        config.search_index_name,
        config.foundry_search_connection_name,
    )
    return ServiceContainer(
        ingestion=ManualIngestionService(
            blob,
            document_intelligence,
            embeddings,
            search,
            foundry,
            config.chunk_size,
            config.chunk_overlap,
        ),
        validation=IngestionValidationService(embeddings, search, foundry),
    )
