from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery

from manual_ingestion.models import SearchChunk


class AzureSearchIndex:
    def __init__(
        self,
        index_client: Any,
        search_client: Any,
        index_name: str,
        vector_dimensions: int,
    ) -> None:
        self._index_client = index_client
        self._search_client = search_client
        self._index_name = index_name
        self._vector_dimensions = vector_dimensions

    def ensure_index(self) -> None:
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
            SimpleField(
                name="document_id", type=SearchFieldDataType.String, filterable=True, facetable=True
            ),
            SearchableField(name="title", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self._vector_dimensions,
                vector_search_profile_name="manual-vector-profile",
            ),
            SearchField(
                name="section_path",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                searchable=True,
                filterable=True,
            ),
            SimpleField(name="page_start", type=SearchFieldDataType.Int32, filterable=True),
            SimpleField(name="page_end", type=SearchFieldDataType.Int32, filterable=True),
            SimpleField(name="source_url", type=SearchFieldDataType.String),
            SimpleField(name="ordinal", type=SearchFieldDataType.Int32, sortable=True),
        ]
        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="manual-hnsw")],
            profiles=[
                VectorSearchProfile(
                    name="manual-vector-profile",
                    algorithm_configuration_name="manual-hnsw",
                )
            ],
        )
        self._index_client.create_or_update_index(
            SearchIndex(name=self._index_name, fields=fields, vector_search=vector_search)
        )

    def replace_document(self, document_id: str, chunks: Sequence[SearchChunk]) -> int:
        existing_ids = {
            str(result["id"])
            for result in self._search_client.search(
                search_text="*",
                filter=f"document_id eq '{_escape_filter(document_id)}'",
                select=["id"],
                top=1000,
            )
        }
        documents = [
            {
                "id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "title": chunk.title,
                "content": chunk.content,
                "content_vector": list(chunk.content_vector),
                "section_path": list(chunk.section_path),
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "source_url": chunk.source_url,
                "ordinal": chunk.ordinal,
            }
            for chunk in chunks
        ]
        if documents:
            self._search_client.merge_or_upload_documents(documents=documents)

        current_ids = {chunk.chunk_id for chunk in chunks}
        stale_ids = existing_ids - current_ids
        if stale_ids:
            self._search_client.delete_documents(
                documents=[{"id": chunk_id} for chunk_id in sorted(stale_ids)]
            )
        return len(stale_ids)

    def hybrid_search(self, query: str, vector: Sequence[float], top: int = 5) -> list[dict]:
        vector_query = VectorizedQuery(
            vector=list(vector),
            k_nearest_neighbors=top,
            fields="content_vector",
        )
        results = self._search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            select=[
                "id",
                "document_id",
                "title",
                "content",
                "section_path",
                "page_start",
                "page_end",
                "source_url",
            ],
            top=top,
        )
        return [dict(result) for result in results]


def _escape_filter(value: str) -> str:
    return value.replace("'", "''")
