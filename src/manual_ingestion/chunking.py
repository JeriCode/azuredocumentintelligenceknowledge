from __future__ import annotations

from hashlib import sha256

from manual_ingestion.models import ExtractedDocument, ExtractedParagraph, SearchChunk


def _chunk_id(document_id: str, ordinal: int, content: str) -> str:
    digest = sha256(content.encode("utf-8")).hexdigest()[:16]
    return f"{document_id}-{ordinal:06d}-{digest}"


def chunk_document(
    document: ExtractedDocument,
    *,
    max_characters: int,
    overlap_characters: int,
) -> list[SearchChunk]:
    if max_characters <= 0:
        raise ValueError("max_characters must be greater than zero")
    if overlap_characters < 0 or overlap_characters >= max_characters:
        raise ValueError("overlap_characters must be between zero and max_characters")

    chunks: list[SearchChunk] = []
    section_path: list[str] = []
    buffer: list[ExtractedParagraph] = []
    buffer_length = 0

    def flush() -> None:
        nonlocal buffer, buffer_length
        if not buffer:
            return
        content = "\n\n".join(paragraph.text.strip() for paragraph in buffer).strip()
        if not content:
            buffer = []
            buffer_length = 0
            return
        ordinal = len(chunks)
        chunks.append(
            SearchChunk(
                chunk_id=_chunk_id(document.document_id, ordinal, content),
                document_id=document.document_id,
                title=document.title,
                content=content,
                section_path=tuple(section_path),
                page_start=min(paragraph.page_number for paragraph in buffer),
                page_end=max(paragraph.page_number for paragraph in buffer),
                source_url=document.source_url,
                ordinal=ordinal,
            )
        )

        if overlap_characters == 0:
            buffer = []
        else:
            retained: list[ExtractedParagraph] = []
            retained_length = 0
            for paragraph in reversed(buffer):
                retained.insert(0, paragraph)
                retained_length += len(paragraph.text) + 2
                if retained_length >= overlap_characters:
                    break
            buffer = retained
        buffer_length = sum(len(paragraph.text) + 2 for paragraph in buffer)

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        if paragraph.role in {"sectionHeading", "title"}:
            flush()
            if paragraph.role == "title":
                section_path = []
            else:
                section_path = [text]
            continue
        projected_length = buffer_length + len(text) + (2 if buffer else 0)
        if buffer and projected_length > max_characters:
            flush()
        buffer.append(ExtractedParagraph(text=text, page_number=paragraph.page_number))
        buffer_length += len(text) + (2 if len(buffer) > 1 else 0)

    flush()
    return chunks