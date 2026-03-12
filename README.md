# Protocrawl

An agent-native system for building a structured knowledge base of sequencing protocols. Six AI agents work in a sequential pipeline to discover, triage, parse, normalize, format, and publish protocol definitions into a canonical schema.

## Architecture

```
Source Scout → Triage → Parser → Normalizer → Formatter → Publisher
```

| Agent | Role |
|-------|------|
| **Source Scout** | Discovers protocol sources from seed URLs, arXiv, and GitHub |
| **Triage** | Classifies relevance and assigns assay categories |
| **Parser** | Extracts metadata, read structures, barcodes, adapters, reagents |
| **Normalizer** | Assembles parsed data into the canonical Protocol schema with confidence scoring |
| **Formatter** | Generates summaries, read diagrams, and JSON output |
| **Publisher** | Confidence-gated publishing: auto-publish (>=0.85) or route to human review |

Built with:
- **Google ADK** — `SequentialAgent` + `LlmAgent` orchestration
- **Gemini API** — default model `gemini-3.1-pro-preview`
- **FastAPI** — REST API + Jinja2 review UI
- **PostgreSQL** — async via SQLAlchemy 2.0 + asyncpg
- **Pydantic v2** — canonical protocol schema with 20+ fields

## Protocol Schema

Each protocol captures:
- Read geometry (read type, lengths, segment-level layout)
- Barcode specifications (cell barcode, UMI, sample index)
- Adapters, reagent kits, protocol steps
- QC expectations and failure modes
- Citations and source URLs
- Confidence score and review status

## Quickstart

### Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Gemini API key

### Setup

```bash
# Clone and install
git clone <repo-url> && cd protocrawl
pip install -e ".[dev]"

# Copy environment config
cp .env.example .env
# Edit .env with your Gemini API key and database URL

# Start PostgreSQL
docker compose up -d

# Run database migrations
alembic upgrade head

# Load seed protocols
protocrawl seed
```

### CLI Commands

```bash
# Load seed protocols into the database
protocrawl seed --seeds-dir seeds/protocols

# List protocols
protocrawl list
protocrawl list --assay scRNA-seq

# Submit a new protocol source URL and ingest it immediately
protocrawl submit --url https://example.com/protocol-page --notes "vendor doc"

# Submit a local PDF or text file directly
protocrawl submit --file /path/to/protocol.pdf --notes "local pdf"

# List recent submissions
protocrawl submissions

# Run the full agent pipeline
protocrawl run --dry-run          # Preview sources
protocrawl run                    # Execute pipeline

# Start the API server
protocrawl serve
```

### API Endpoints

```
GET  /health                          Health check
GET  /protocols                       List protocols (filter: ?assay_family=)
GET  /protocols/{slug}                Protocol detail
GET  /protocols/{slug}/read-geometry  Read geometry detail
GET  /protocols/{slug}/seqspec        Seqspec artifact (json or ?format=yaml)
GET  /protocols/{slug}/versions       Version history
GET  /reviews                         Pending review requests
GET  /reviews/{id}                    Review detail with read diagram
POST /reviews/{id}/decide             Approve or reject a protocol
POST /submissions                     Submit a source URL and ingest it
POST /submissions/upload              Upload a local file and ingest it
GET  /submissions                     List ingestion submissions
GET  /submissions/{id}                Submission detail
POST /submissions/{id}/run            Re-run a submission
POST /pipeline/run                    Ingest seed source URLs
POST /slack/commands                  Slack slash-command endpoint
```

## Slack Usage

Set these env vars in `.env`:

```bash
PROTOCRAWL_SLACK_SIGNING_SECRET=...
PROTOCRAWL_SLACK_BOT_TOKEN=...
PROTOCRAWL_SLACK_APP_TOKEN=...
```

Run the API:

```bash
protocrawl serve
```

Expose it to Slack locally, for example with ngrok:

```bash
ngrok http 8000
```

Create a Slack slash command such as `/protocrawl` and point it to:

```text
https://<your-public-host>/slack/commands
```

Then use these command forms in Slack:

```text
/protocrawl protocol smart-seq2
/protocrawl read smart-seq2
/protocrawl reviews
/protocrawl review <review-uuid> approve
/protocrawl review <review-uuid> reject
```

The Slack endpoint currently supports slash-command style interactions. Querying a protocol returns its summary, `read` returns the read diagram, `reviews` lists pending reviews, and `review ... approve|reject` updates review status in the same database used by the API and CLI.

## Seed Protocols

21 curated protocols across 5 assay families:

| Family | Protocols |
|--------|-----------|
| scRNA-seq | 10x Chromium 3'/5', Drop-seq, Smart-seq2, inDrop, PARSE, CEL-Seq2, STRT-seq, SPLiT-seq, 10x Flex |
| scATAC-seq | 10x ATAC, sci-ATAC-seq |
| Spatial | Visium, Visium HD, Slide-seq, MERFISH, 10x Xenium |
| Multiome | 10x Multiome |
| Bulk RNA-seq | TruSeq Stranded mRNA |
| CITE-seq | CITE-seq |

## Development

```bash
# Run tests
pytest tests/unit/ -v

# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Type check
mypy src/protocrawl/
```

## Deployment

Infrastructure configs are in `infra/`:

- **`main.tf`** — Terraform config for Cloud SQL, Cloud Run, GCS, Artifact Registry, IAM
- **`setup.sh`** — gcloud CLI alternative for provisioning

```bash
# Terraform
cd infra
terraform init
terraform plan -var="project_id=your-project" -var="db_password=secret"
terraform apply

# Or gcloud CLI
bash infra/setup.sh
```

The `Dockerfile` is production-ready with multi-stage build, non-root user, and health check.

## Project Structure

```
src/protocrawl/
  agents/             # 6 ADK agents (source_scout, triage, parser, normalizer, formatter, publisher)
    root_agent.py     # SequentialAgent pipeline wiring
  api/                # FastAPI app, routes, templates
  db/                 # SQLAlchemy tables, repositories, migrations
  llm/                # Gemini API client helpers
  models/             # Pydantic models (protocol, review, source, enums)
  config.py           # Pydantic Settings
  cli.py              # Click CLI (seed, serve, run, list, submit, submissions)
seeds/
  protocols/          # 21 YAML seed files
  sources.yaml        # Curated source URLs and search keywords
infra/                # Terraform + gcloud deployment configs
tests/unit/           # 61 unit tests
```

## License

See [LICENSE](LICENSE).
