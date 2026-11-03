from manual_ingestion.chunking import chunk_document
from manual_ingestion.models import ExtractedDocument, ExtractedParagraph


def _document() -> ExtractedDocument:
    return ExtractedDocument(
        document_id="manual-1",
        title="Operator Manual",
        source_name="manual.pdf",
        source_url="https://example/manual.pdf",
        paragraphs=(
            ExtractedParagraph("Safety", 1, "sectionHeading"),
            ExtractedParagraph("Wear eye protection before operation.", 1),
            ExtractedParagraph("Disconnect power before maintenance.", 2),
            ExtractedParagraph("Calibration", 3, "sectionHeading"),
            ExtractedParagraph("Use the calibration menu to set zero.", 3),
        ),
    )


def test_chunk_document_preserves_source_metadata() -> None:
    chunks = chunk_document(_document(), max_characters=60, overlap_characters=10)

    assert len(chunks) >= 2
    assert chunks[0].section_path == ("Safety",)
    assert chunks[0].page_start == 1
    assert chunks[0].source_url == "https://example/manual.pdf"
    assert chunks[-1].section_path == ("Calibration",)


def test_chunk_ids_are_stable() -> None:
    first = chunk_document(_document(), max_characters=60, overlap_characters=10)
    second = chunk_document(_document(), max_characters=60, overlap_characters=10)

    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
