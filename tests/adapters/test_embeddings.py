from types import SimpleNamespace

from manual_ingestion.adapters.embeddings import AzureOpenAIEmbeddings


class EmbeddingsClientStub:
    def __init__(self) -> None:
        self.embeddings = self

    def create(self, **kwargs: object) -> SimpleNamespace:
        assert kwargs["model"] == "embedding-deployment"
        assert kwargs["dimensions"] == 2
        return SimpleNamespace(
            data=[
                SimpleNamespace(index=1, embedding=[0.3, 0.4]),
                SimpleNamespace(index=0, embedding=[0.1, 0.2]),
            ]
        )


def test_embed_restores_input_order() -> None:
    adapter = AzureOpenAIEmbeddings(EmbeddingsClientStub(), "embedding-deployment", 2)

    vectors = adapter.embed(["first", "second"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
