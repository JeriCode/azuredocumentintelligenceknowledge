from pathlib import Path

import pytest

from manual_ingestion.ingestion import IngestionError, ManualIngestionService
from manual_ingestion.models import ExtractedDocument, ExtractedParagraph


class BlobStub:
    def upload_pdf(self, path: Path, document_id: str) -> str:
        return f"https://example/{document_id}/{path.name}"

    def create_read_url(self, path: Path, document_id: str) -> str:
        return f"https://example/{document_id}/{path.name}?read-only-sas"


class ExtractorStub:
    def extract(
        self,
        path: Path,
        document_id: str,
        source_url: str,
        analysis_url: str,
    ) -> ExtractedDocument:
        assert analysis_url.endswith("?read-only-sas")
        return ExtractedDocument(
            document_id=document_id,
            title="Manual",
            source_name=path.name,
            source_url=source_url,
            paragraphs=(ExtractedParagraph("Indexable content", 1),),
        )


class EmbeddingsStub:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]


class SearchStub:
    def __init__(self) -> None:
        self.chunks = []

    def ensure_index(self) -> None:
        return None

    def replace_document(self, document_id: str, chunks: list) -> int:
        self.chunks = list(chunks)
        return 2

    def hybrid_search(self, query: str, vector: list[float], top: int = 5) -> list[dict]:
        return []


class FoundryStub:
    def __init__(self) -> None:
        self.attached = False

    def ensure_search_tool(self) -> str:
        self.attached = True
        return "2"

    def validate_agent(self) -> None:
        return None


def test_ingest_runs_each_stage(tmp_path: Path) -> None:
    pdf = tmp_path / "manual.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    search = SearchStub()
    foundry = FoundryStub()
    service = ManualIngestionService(
        BlobStub(),
        ExtractorStub(),
        EmbeddingsStub(),
        search,
        foundry,
        chunk_size=200,
        chunk_overlap=20,
    )

    summary = service.ingest(pdf)

    assert summary.chunks_indexed == 1
    assert summary.stale_chunks_removed == 2
    assert search.chunks[0].content_vector == (0.1, 0.2)
    assert foundry.attached is True


def test_ingest_rejects_non_pdf(tmp_path: Path) -> None:
    text_file = tmp_path / "manual.txt"
    text_file.write_text("not a PDF")
    service = ManualIngestionService(
        BlobStub(),
        ExtractorStub(),
        EmbeddingsStub(),
        SearchStub(),
        FoundryStub(),
        chunk_size=200,
        chunk_overlap=20,
    )

    with pytest.raises(IngestionError, match=".pdf extension"):
        service.ingest(text_file)
