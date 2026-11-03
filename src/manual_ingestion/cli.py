from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from manual_ingestion.config import AppConfig
from manual_ingestion.services import build_services


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="manual-ingestion",
        description="Ingest PDF manuals into Azure AI Search for an existing Foundry agent.",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable diagnostic logging")
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest", help="Upload, extract, chunk, embed, and index a PDF")
    ingest.add_argument("pdf", type=Path, help="Local path to the PDF manual")

    validate = commands.add_parser("validate", help="Run representative hybrid queries")
    validate.add_argument(
        "--query",
        action="append",
        required=True,
        help="Representative query; repeat for multiple queries",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        services = build_services(AppConfig.from_env())
        if args.command == "ingest":
            summary = services.ingestion.ingest(args.pdf)
            print(json.dumps(asdict(summary), indent=2))
        else:
            results = services.validation.validate(args.query)
            compact = {
                query: [
                    {
                        "id": match.get("id"),
                        "title": match.get("title"),
                        "page_start": match.get("page_start"),
                        "source_url": match.get("source_url"),
                    }
                    for match in matches
                ]
                for query, matches in results.items()
            }
            print(json.dumps(compact, indent=2))
        return 0
    except Exception as error:
        logging.getLogger(__name__).error("%s", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
