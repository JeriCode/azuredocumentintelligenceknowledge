from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path


def stable_document_id(source_name: str) -> str:
    normalized_name = Path(source_name).name.casefold()
    return sha256(normalized_name.encode("utf-8")).hexdigest()[:32]


@dataclass(frozen=True, slots=True)
class ExtractedParagraph:
    text: str
    page_number: int
    role: str | None = None


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    document_id: str
    title: str
    source_name: str
    source_url: str
    paragraphs: tuple[ExtractedParagraph, ...]


@dataclass(frozen=True, slots=True)
class SearchChunk:
    chunk_id: str
    document_id: str
    title: str
    content: str
    section_path: tuple[str, ...]
    page_start: int
    page_end: int
    source_url: str
    ordinal: int
    content_vector: tuple[float, ...] = field(default_factory=tuple)

    def with_vector(self, vector: list[float]) -> SearchChunk:
        return SearchChunk(
            chunk_id=self.chunk_id,
            document_id=self.document_id,
            title=self.title,
            content=self.content,
            section_path=self.section_path,
            page_start=self.page_start,
            page_end=self.page_end,
            source_url=self.source_url,
            ordinal=self.ordinal,
            content_vector=tuple(vector),
        )


@dataclass(frozen=True, slots=True)
class IngestionSummary:
    document_id: str
    source_url: str
    chunks_indexed: int
    stale_chunks_removed: int
