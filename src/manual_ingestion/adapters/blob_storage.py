from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from azure.storage.blob import BlobSasPermissions, generate_blob_sas


class AzureBlobStorage:
    def __init__(self, service_client: Any, container_name: str) -> None:
        self._service_client = service_client
        self._container_name = container_name

    def upload_pdf(self, path: Path, document_id: str) -> str:
        blob_name = f"{document_id}/{path.name}"
        blob_client = self._service_client.get_blob_client(
            container=self._container_name,
            blob=blob_name,
        )
        with path.open("rb") as stream:
            blob_client.upload_blob(
                stream,
                overwrite=True,
                content_type="application/pdf",
                metadata={"document_id": document_id, "source_name": path.name},
            )
        return blob_client.url

    def create_read_url(self, path: Path, document_id: str) -> str:
        blob_name = f"{document_id}/{path.name}"
        blob_client = self._service_client.get_blob_client(
            container=self._container_name,
            blob=blob_name,
        )
        starts_on = datetime.now(UTC) - timedelta(minutes=5)
        expires_on = datetime.now(UTC) + timedelta(hours=1)
        delegation_key = self._service_client.get_user_delegation_key(
            key_start_time=starts_on,
            key_expiry_time=expires_on,
        )
        sas_token = generate_blob_sas(
            account_name=self._service_client.account_name,
            container_name=self._container_name,
            blob_name=blob_name,
            user_delegation_key=delegation_key,
            permission=BlobSasPermissions(read=True),
            start=starts_on,
            expiry=expires_on,
            protocol="https",
        )
        return f"{blob_client.url}?{sas_token}"
