from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from manual_ingestion.models import ExtractedDocument, SearchChunk


class BlobStorage(Protocol):
    def upload_pdf(self, path: Path, document_id: str) -> str: ...

    def create_read_url(self, path: Path, document_id: str) -> str: ...


class DocumentExtractor(Protocol):
    def extract(
        self,
        path: Path,
        document_id: str,
        source_url: str,
        analysis_url: str,
    ) -> ExtractedDocument: ...


class EmbeddingGenerator(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class SearchIndex(Protocol):
    def ensure_index(self) -> None: ...

    def replace_document(self, document_id: str, chunks: Sequence[SearchChunk]) -> int: ...

    def hybrid_search(self, query: str, vector: Sequence[float], top: int = 5) -> list[dict]: ...


class FoundryKnowledgeSource(Protocol):
    def ensure_search_tool(self) -> str: ...

    def validate_agent(self) -> None: ...
