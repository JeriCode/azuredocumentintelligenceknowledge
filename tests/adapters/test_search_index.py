from manual_ingestion.adapters.search_index import AzureSearchIndex
from manual_ingestion.models import SearchChunk


class IndexClientStub:
    def create_or_update_index(self, index: object) -> None:
        return None


class SearchClientStub:
    def __init__(self) -> None:
        self.uploaded: list[dict] = []
        self.deleted: list[dict] = []

    def search(self, **kwargs: object) -> list[dict]:
        return [{"id": "current"}, {"id": "stale"}]

    def merge_or_upload_documents(self, documents: list[dict]) -> None:
        self.uploaded = documents

    def delete_documents(self, documents: list[dict]) -> None:
        self.deleted = documents


def test_replace_document_upserts_current_and_deletes_stale() -> None:
    client = SearchClientStub()
    adapter = AzureSearchIndex(IndexClientStub(), client, "manuals", 2)
    chunk = SearchChunk(
        chunk_id="current",
        document_id="manual-1",
        title="Manual",
        content="Content",
        section_path=("Safety",),
        page_start=1,
        page_end=1,
        source_url="https://example/manual.pdf",
        ordinal=0,
        content_vector=(0.1, 0.2),
    )

    removed = adapter.replace_document("manual-1", [chunk])

    assert removed == 1
    assert client.uploaded[0]["id"] == "current"
    assert client.deleted == [{"id": "stale"}]
