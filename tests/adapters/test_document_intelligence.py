from pathlib import Path
from types import SimpleNamespace

from manual_ingestion.adapters.document_intelligence import AzureDocumentIntelligence


class PollerStub:
    def result(self) -> SimpleNamespace:
        return SimpleNamespace(
            paragraphs=[
                SimpleNamespace(
                    content="Service Manual",
                    role="title",
                    bounding_regions=[SimpleNamespace(page_number=1)],
                ),
                SimpleNamespace(
                    content="Disconnect power before service.",
                    role=None,
                    bounding_regions=[SimpleNamespace(page_number=4)],
                ),
            ]
        )


class ClientStub:
    def begin_analyze_document(self, **kwargs: object) -> PollerStub:
        assert kwargs["model_id"] == "prebuilt-layout"
        assert kwargs["content_type"] == "application/json"
        request = kwargs["body"]
        assert request.url_source == "https://example/manual.pdf?read-only-sas"
        return PollerStub()


def test_extract_maps_title_pages_and_source(tmp_path: Path) -> None:
    pdf = tmp_path / "manual.pdf"
    pdf.write_bytes(b"%PDF-1.7")

    document = AzureDocumentIntelligence(ClientStub()).extract(
        pdf,
        "document-1",
        "https://example/manual.pdf",
        "https://example/manual.pdf?read-only-sas",
    )

    assert document.title == "Service Manual"
    assert document.paragraphs[1].page_number == 4
    assert document.source_url == "https://example/manual.pdf"
