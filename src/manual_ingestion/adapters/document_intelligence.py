from __future__ import annotations

from pathlib import Path
from typing import Any

from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

from manual_ingestion.models import ExtractedDocument, ExtractedParagraph


class AzureDocumentIntelligence:
    def __init__(self, client: Any) -> None:
        self._client = client

    def extract(
        self,
        path: Path,
        document_id: str,
        source_url: str,
        analysis_url: str,
    ) -> ExtractedDocument:
        poller = self._client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=AnalyzeDocumentRequest(url_source=analysis_url),
            content_type="application/json",
        )
        result = poller.result()
        paragraphs: list[ExtractedParagraph] = []
        title = path.stem

        for paragraph in result.paragraphs or []:
            text = (paragraph.content or "").strip()
            if not text:
                continue
            role = str(paragraph.role) if paragraph.role else None
            if role and "." in role:
                role = role.rsplit(".", maxsplit=1)[-1]
            page_number = 1
            if paragraph.bounding_regions:
                page_number = paragraph.bounding_regions[0].page_number
            if role == "title":
                title = text
            paragraphs.append(
                ExtractedParagraph(text=text, page_number=page_number, role=role)
            )

        if not paragraphs:
            raise ValueError("Document Intelligence returned no paragraphs for the PDF")

        return ExtractedDocument(
            document_id=document_id,
            title=title,
            source_name=path.name,
            source_url=source_url,
            paragraphs=tuple(paragraphs),
        )
