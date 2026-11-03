from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class AzureOpenAIEmbeddings:
    def __init__(self, client: Any, deployment_name: str, dimensions: int) -> None:
        self._client = client
        self._deployment_name = deployment_name
        self._dimensions = dimensions

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(
            model=self._deployment_name,
            input=list(texts),
            dimensions=self._dimensions,
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        return [list(item.embedding) for item in ordered]
