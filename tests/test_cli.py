from types import SimpleNamespace

from manual_ingestion import cli
from manual_ingestion.models import IngestionSummary


def test_ingest_command_prints_summary(monkeypatch, tmp_path, capsys) -> None:
    pdf = tmp_path / "manual.pdf"
    pdf.write_bytes(b"%PDF-1.7")
    ingestion = SimpleNamespace(
        ingest=lambda _: IngestionSummary(
            document_id="document-1",
            source_url="https://example/manual.pdf",
            chunks_indexed=3,
            stale_chunks_removed=1,
        )
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: object())
    monkeypatch.setattr(
        cli,
        "build_services",
        lambda _: SimpleNamespace(ingestion=ingestion, validation=SimpleNamespace()),
    )

    exit_code = cli.main(["ingest", str(pdf)])

    assert exit_code == 0
    assert '"chunks_indexed": 3' in capsys.readouterr().out


def test_validate_command_prints_compact_citations(monkeypatch, capsys) -> None:
    queries = []
    validation = SimpleNamespace(
        validate=lambda values: queries.append(values)
        or {
            "reset": [
                {
                    "id": "chunk-1",
                    "title": "Manual",
                    "page_start": 4,
                    "source_url": "https://example/manual.pdf",
                    "content": "Not included in CLI output",
                }
            ]
        }
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: object())
    monkeypatch.setattr(
        cli,
        "build_services",
        lambda _: SimpleNamespace(ingestion=SimpleNamespace(), validation=validation),
    )

    exit_code = cli.main(["validate", "--query", "reset"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert queries == [["reset"]]
    assert '"page_start": 4' in output
    assert '"content"' not in output