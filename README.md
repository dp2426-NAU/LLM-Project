# LLM Project Portfolio

Production-grade AI systems built with LLMs, RAG pipelines, and multi-agent architectures.

---

## Projects

### [RegDelta](./RegDelta/) — Regulatory Change Impact Analyzer
> Detects how SEC/FINRA regulation amendments affect internal compliance policies.

**Stack:** FastAPI · ChromaDB · sentence-transformers · OpenAI/Ollama · SQLite · Docker

**What it does:**
- Ingests regulatory documents (SEC, FINRA, Basel) and internal policy corpus into separate vector collections
- Detects section-level changes between regulation versions using a custom diff engine
- Retrieves semantically affected internal policies via dual-collection RAG
- Generates a structured impact report with risk level, affected policies, and recommended actions

```
Regulation v1 + v2 → Diff Engine → Changed Sections
                                          ↓
Internal Policies → ChromaDB → Retriever → LLM → Impact Report
```

**Key endpoints:**
- `POST /api/v1/ingest/regulation` — ingest a regulation version
- `POST /api/v1/ingest/policy` — ingest an internal policy
- `POST /api/v1/analyze/delta` — generate impact report between versions
- `GET  /api/v1/reports/{id}` — retrieve a saved report

---

### [SynapseIQ](./SynapseIQ/) — Multi-Agent Research Intelligence & Synthesis Platform
> Four specialized AI agents collaborate to produce rigorous, self-evaluated knowledge synthesis.

**Stack:** FastAPI · ChromaDB · sentence-transformers · OpenAI/Ollama · Jinja2+YAML Prompts · SQLite · Docker

**What it does:**
- Ingests any document corpus (PDFs, text, markdown) into a persistent vector store
- Runs a 4-stage agent pipeline: Researcher → Critic → Synthesizer → Validator
- Each agent uses a versioned, hot-reloadable YAML+Jinja2 prompt template
- Produces a structured knowledge artifact with a 4-dimension quality scorecard (PASS/FAIL verdict)
- Tracks token usage, latency, and estimated cost per session in SQLite

```
Query → ChromaDB (retrieval)
            ↓
     ResearcherAgent → CriticAgent → SynthesizerAgent → ValidatorAgent
            ↓                                   ↓
     AgentContext (shared state)        EvaluationResult
            ↓                                   ↓
     PipelineTracer (SQLite)       Composite Score + Verdict
```

**Key endpoints:**
- `POST /api/v1/synthesize` — run full agent pipeline
- `POST /api/v1/ingest` — add documents to corpus
- `GET  /api/v1/analytics` — session history, agent stats, cost summary
- `GET  /api/v1/agents/status` — pipeline configuration

---

## Quick Start

Each project runs independently. Navigate into the project folder and follow its README.

```bash
# RegDelta
cd RegDelta
pip install -r requirements.txt
cp .env.example .env   # add OPENAI_API_KEY
python scripts/seed_sample_data.py
uvicorn app.main:app --reload

# SynapseIQ
cd SynapseIQ
pip install -r requirements.txt
cp .env.example .env   # add OPENAI_API_KEY
uvicorn backend.main:app --reload --port 8001
```

Both support **Ollama** (local LLMs, zero API cost) by setting `LLM_PROVIDER=ollama` in `.env`.

---

## Shared Design Principles

- **Modular architecture** — no monolithic scripts; every concern is a separate module
- **Swappable LLM backend** — OpenAI or Ollama, switched via a single env variable
- **Production logging** — structured JSON logs, SQLite analytics, per-session tracing
- **Cost awareness** — token budgets per component, cost estimation built in
- **Testable** — pytest suites with unit, integration, and evaluation layers
- **Containerized** — Dockerfiles with embedding model pre-fetched at build time
