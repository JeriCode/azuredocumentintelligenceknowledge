from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from manual_ingestion.adapters.interfaces import (
    BlobStorage,
    DocumentExtractor,
    EmbeddingGenerator,
    FoundryKnowledgeSource,
    SearchIndex,
)
from manual_ingestion.chunking import chunk_document
from manual_ingestion.models import IngestionSummary, SearchChunk, stable_document_id


class IngestionError(RuntimeError):
    """Raised when an ingestion or validation invariant is not satisfied."""


class ManualIngestionService:
    def __init__(
        self,
        blob_storage: BlobStorage,
        document_extractor: DocumentExtractor,
        embeddings: EmbeddingGenerator,
        search_index: SearchIndex,
        foundry: FoundryKnowledgeSource,
        chunk_size: int,
        chunk_overlap: int,
        embedding_batch_size: int = 16,
    ) -> None:
        self._blob_storage = blob_storage
        self._document_extractor = document_extractor
        self._embeddings = embeddings
        self._search_index = search_index
        self._foundry = foundry
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._embedding_batch_size = embedding_batch_size

    def ingest(self, path: Path) -> IngestionSummary:
        _validate_pdf(path)
        document_id = stable_document_id(path.name)
        source_url = self._blob_storage.upload_pdf(path, document_id)
        analysis_url = self._blob_storage.create_read_url(path, document_id)
        document = self._document_extractor.extract(
            path,
            document_id,
            source_url,
            analysis_url,
        )
        chunks = chunk_document(
            document,
            max_characters=self._chunk_size,
            overlap_characters=self._chunk_overlap,
        )
        if not chunks:
            raise IngestionError("The extracted PDF did not contain indexable text")

        embedded_chunks = self._embed_chunks(chunks)
        self._search_index.ensure_index()
        stale_chunks_removed = self._search_index.replace_document(
            document_id,
            embedded_chunks,
        )
        self._foundry.ensure_search_tool()
        return IngestionSummary(
            document_id=document_id,
            source_url=source_url,
            chunks_indexed=len(embedded_chunks),
            stale_chunks_removed=stale_chunks_removed,
        )

    def _embed_chunks(self, chunks: Sequence[SearchChunk]) -> list[SearchChunk]:
        embedded: list[SearchChunk] = []
        for offset in range(0, len(chunks), self._embedding_batch_size):
            batch = chunks[offset : offset + self._embedding_batch_size]
            vectors = self._embeddings.embed([chunk.content for chunk in batch])
            if len(vectors) != len(batch):
                raise IngestionError(
                    f"Embedding service returned {len(vectors)} vectors for {len(batch)} chunks"
                )
            embedded.extend(
                chunk.with_vector(vector) for chunk, vector in zip(batch, vectors, strict=True)
            )
        return embedded


class IngestionValidationService:
    def __init__(
        self,
        embeddings: EmbeddingGenerator,
        search_index: SearchIndex,
        foundry: FoundryKnowledgeSource,
    ) -> None:
        self._embeddings = embeddings
        self._search_index = search_index
        self._foundry = foundry

    def validate(self, queries: Sequence[str]) -> dict[str, list[dict]]:
        if not queries:
            raise IngestionError("At least one representative query is required")
        self._foundry.validate_agent()
        results: dict[str, list[dict]] = {}
        for query in queries:
            vectors = self._embeddings.embed([query])
            if len(vectors) != 1:
                raise IngestionError("Embedding service did not return a query vector")
            matches = self._search_index.hybrid_search(query, vectors[0])
            if not matches:
                raise IngestionError(f"Hybrid query returned no results: {query!r}")
            results[query] = matches
        return results


def _validate_pdf(path: Path) -> None:
    if not path.is_file():
        raise IngestionError(f"PDF file does not exist: {path}")
    if path.suffix.casefold() != ".pdf":
        raise IngestionError(f"Input must have a .pdf extension: {path}")
    with path.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise IngestionError(f"Input is not a valid PDF file: {path}")
