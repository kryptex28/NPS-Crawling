# NPS-Crawling

An end-to-end framework for crawling, parsing, preprocessing, classifying, and analyzing corporate financial filings (such as SEC Edgar filings) for Net Promoter Score (NPS), ESG metrics, and corporate disclosures.

---

## Key Features

- **SEC Edgar Crawling Engine**: Built on Scrapy for automated discovery, query pre-fetching, and bulk downloading of corporate filings (10-K, 10-Q, 8-K, 20-F, DEF 14A, etc.).
- **Semantic Preprocessing**: Cleans HTML/XML content, applies keyword scope filtering, sentence-boundary extraction, and embedding similarity ranking via SentenceTransformers (`all-MiniLM-L6-v2`).
- **ML / LLM Classification**: Supports zero-shot and few-shot text classification through HuggingFace Transformers (PyTorch) or external Ollama HTTP servers.
- **Dual User Interfaces**:
  - **Command-Line Interface (CLI)**: For batch operations, script execution, and headless automation.
  - **Interactive Terminal UI (TUI)**: Rich Textual dashboard for project selection, live crawling control, real-time log streaming, and database inspection.
- **Decoupled Data Architecture**: Automated PostgreSQL setup via Docker Compose alongside structured dataset storage (`json_raw/`, `json_processed/`, `json_classified/`).

---

## Installation & Setup

### 1. Prerequisites
- **Python**: 3.10 or higher
- **Docker & Docker Compose**: Required for local PostgreSQL database container management.

### 2. Install Package
Clone the repository and install the package in editable mode:

```bash
git clone https://github.com/kryptex28/NPS-Crawling.git
cd NPS-Crawling

# Recommended: create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Linux/macOS

# Install package in editable mode
pip install -e .
```

---

## Usage Guide

### Command Line Interface (CLI)

The package installs a unified CLI entrypoint: `nps-crawling`.

#### 1. Load a Project Configuration
Before executing pipelines, activate a project specification defined in the `projects/` directory (e.g., `projects/default.json`):

```bash
nps-crawling load default
```

#### 2. Crawl Filings
Executes the Scrapy spider pipeline:

```bash
nps-crawling crawl
```

**Common Crawl Flags:**
- `--dry-run`: Simulate crawling without saving data.
- `--db-only`: Crawl metadata and update database without saving raw files.
- `--prefetch-only`: Execute query pre-fetching without full filing body crawl.
- `--ignore-lookup`: Force re-crawling regardless of existing database records.
- `--limit N`: Limit the number of filings to crawl (e.g., `--limit 100`).

#### 3. Preprocess Filings
Parse HTML/XML, apply keyword filters, compute sentence embeddings, and extract context snippets:

```bash
nps-crawling process
```

#### 4. Classify Text Snippets
Run ML / LLM classification models against preprocessed text chunks:

```bash
nps-crawling classify
```
*Use `--force` to overwrite existing classification outputs.*

#### 5. Display Results Summary
Summarize and export metrics:

```bash
nps-crawling display
```

---

## Interactive Terminal UI (TUI)

Launch the interactive terminal dashboard powered by Textual:

```bash
python tui/app.py
```

The TUI provides workspace views for:
- **Project Management**: Switch active projects and create new project specifications.
- **Query Setup**: Edit SEC ticker symbols, CIKs, and filing type filters.
- **Pipeline Execution**: Trigger Crawl, Preprocess, and Classification stages with real-time log output.
- **Database Inspector**: Monitor PostgreSQL database connection health, row counts, and table schemas.

---

## Repository Structure

```
NPS-Crawling/
├── src/nps_crawling/         # Core Python package
│   ├── __main__.py           # CLI entrypoint & Docker orchestrator
│   ├── config.py             # Global runtime configuration state
│   ├── project_config.py     # Project JSON specification loader
│   ├── crawler/              # Scrapy spiders, pattern strategies & storage pipeline
│   ├── preprocessing/        # Text cleaning, filtering & vector similarity
│   ├── classification/       # Dataset splitting, LLM prompting & model pipelines
│   ├── db/                   # SQLAlchemy / SQLModel DB adapter & PostgreSQL models
│   ├── llm/                  # HuggingFace & Ollama LLM provider interfaces
│   ├── results/              # Results processing & summary aggregators
│   └── utils/                # EventBus pub/sub stream & project management helpers
├── tui/                      # Textual User Interface application
│   ├── app.py                # Main TUI app controller
│   ├── widgets/              # Page view & shell widgets
│   ├── screens/              # Modal configuration dialogs
│   └── models/               # Singleton domain models
├── projects/                 # Project JSON specification files
├── docker/                   # Docker Compose setup for local PostgreSQL
└── data/                     # Output datasets (json_raw, json_processed, json_classified)
```

---

## Development & Code Quality

### Code Linting & Formatting
Run Tox for linting:

```bash
tox -e lint
```

Auto-fix lint issues:
```bash
tox -e lint -- --fix
```

### Running Tests
Execute pytest suite:

```bash
pytest
```