from pathlib import Path

from manual_ingestion.adapters import blob_storage
from manual_ingestion.adapters.blob_storage import AzureBlobStorage


class BlobClientStub:
    url = "https://account.blob.core.windows.net/manuals/document-1/manual.pdf"

    def upload_blob(self, *args: object, **kwargs: object) -> None:
        return None


class ServiceClientStub:
    account_name = "account"

    def __init__(self) -> None:
        self.blob_client = BlobClientStub()
        self.delegation_key_args = None

    def get_blob_client(self, **kwargs: str) -> BlobClientStub:
        assert kwargs == {"container": "manuals", "blob": "document-1/manual.pdf"}
        return self.blob_client

    def get_user_delegation_key(self, **kwargs: object) -> object:
        self.delegation_key_args = kwargs
        return "delegation-key"


def test_create_read_url_uses_short_lived_read_only_sas(
    tmp_path: Path,
    monkeypatch,
) -> None:
    service_client = ServiceClientStub()
    sas_args = {}

    def generate_blob_sas(**kwargs: object) -> str:
        sas_args.update(kwargs)
        return "sp=r&sig=redacted"

    monkeypatch.setattr(blob_storage, "generate_blob_sas", generate_blob_sas)
    adapter = AzureBlobStorage(service_client, "manuals")

    read_url = adapter.create_read_url(tmp_path / "manual.pdf", "document-1")

    assert read_url == f"{service_client.blob_client.url}?sp=r&sig=redacted"
    assert sas_args["container_name"] == "manuals"
    assert sas_args["blob_name"] == "document-1/manual.pdf"
    assert sas_args["user_delegation_key"] == "delegation-key"
    assert sas_args["protocol"] == "https"
    permission = sas_args["permission"]
    assert permission.read
    assert not permission.write
    assert not permission.delete
    assert not permission.list
    assert service_client.delegation_key_args is not None
    key_expiry_time = service_client.delegation_key_args["key_expiry_time"]
    key_start_time = service_client.delegation_key_args["key_start_time"]
    assert key_expiry_time > key_start_time