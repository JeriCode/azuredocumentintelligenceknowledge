# PDF Manual Knowledge Ingestion

An on-demand Python CLI that uploads a PDF manual to private Azure Blob Storage,
extracts layout with Azure AI Document Intelligence, generates Azure OpenAI embeddings,
and replaces that manual's chunks in an Azure AI Search hybrid index. It then attaches the
index to an existing Microsoft Foundry prompt agent as an Azure AI Search tool.

## Prerequisites

- Python 3.11 or newer
- Azure CLI authenticated with `az login` for local development
- Existing Blob Storage, Document Intelligence, Azure AI Search, Azure OpenAI, and
  Microsoft Foundry resources
- A project connection from the Foundry project to Azure AI Search

The local identity or deployed managed identity needs data-plane permissions for each
resource. Typical roles include Storage Blob Data Contributor, Storage Blob Delegator,
Cognitive Services User, Search Index Data Contributor, Search Service Contributor, and
the applicable Foundry project role. Use least privilege appropriate to the environment.
Ingestion creates a one-hour, HTTPS-only, blob-scoped read SAS using a user-delegation key
for Document Intelligence; the SAS is not stored in Search citations.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Set the values documented in `.env.example` in your shell or environment manager. The CLI
uses `DefaultAzureCredential`; it does not accept account keys, SAS tokens, or API keys.

## Ingest

```powershell
manual-ingestion ingest C:\manuals\operator-manual.pdf
```

Re-ingesting the same filename uses the same document identity. Current chunks are upserted
and stale chunk IDs are deleted, preventing outdated duplicate results.

## Validate

```powershell
manual-ingestion validate --query "How do I calibrate the device?" --query "What PPE is required?"
```

Validation confirms the Foundry agent endpoint is configured and executes representative
hybrid text/vector queries against Azure AI Search. The command exits nonzero when a query
returns no matches or when the agent/search connection is incompatible.

## Container

Create `.env`, then run the on-demand service with an explicit command and mounted PDF path:

```powershell
docker compose run --rm manual-ingestion ingest /workspace/manual.pdf
```

## Development

```powershell
python -m ruff check src tests
python -m pytest
```

Azure SDK clients live only in `src/manual_ingestion/adapters`. The ingestion service depends
on protocols, allowing each pipeline stage to be tested independently without Azure access.