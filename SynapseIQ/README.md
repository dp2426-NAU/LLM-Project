# SynapseIQ

**Multi-Agent Research Intelligence & Synthesis Platform**

> Four specialized AI agents collaborate to produce rigorous, self-evaluated knowledge synthesis from document corpora.

---

## What It Does

You provide a corpus of documents (PDFs, text files, markdown) and a research question. SynapseIQ runs a 4-stage agent pipeline:

| Stage | Agent | Role |
|-------|-------|------|
| 1 | **Researcher** | Extracts structured findings from semantically retrieved chunks |
| 2 | **Critic** | Identifies logical gaps, bias signals, and unsupported claims |
| 3 | **Synthesizer** | Produces the full knowledge artifact (brief/standard/detailed) |
| 4 | **Validator** | Scores the output on coherence, relevance, factuality, completeness |

The final response includes the synthesis document, a 4-dimension quality scorecard, full agent traces, and a PASS/CONDITIONAL_PASS/FAIL verdict.

---

## Architecture

```
User → FastAPI → SynapseOrchestrator
                      │
                 ChromaDB (retrieval)
                      │
           Researcher → Critic → Synthesizer → Validator
                      │              │
               PromptEngine      LLMClient
              (YAML+Jinja2)   (OpenAI/Ollama)
                      │
                 PipelineEvaluator → EvaluationResult
                      │
               SQLite Analytics DB
```

Full architecture diagrams (ASCII 3D + Mermaid) are in [docs/PROJECT_DOCUMENTATION.md](docs/PROJECT_DOCUMENTATION.md).

---

## Quick Start

```bash
git clone https://github.com/dp2426-NAU/LLM-Project.git
cd synapseiq
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your OPENAI_API_KEY
uvicorn backend.main:app --reload
```

API docs: `http://localhost:8000/api/v1/docs`

---

## Seed the Corpus

```bash
# Ingest the included sample documents
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"file_path": "data/sample_corpus/transformers_overview.txt", "source_label": "transformers"}'

curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"file_path": "data/sample_corpus/llm_finetuning.txt", "source_label": "finetuning"}'
```

---

## Run a Synthesis

```bash
curl -X POST http://localhost:8000/api/v1/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Compare LoRA and full fine-tuning approaches for adapting large language models",
    "output_format": "standard",
    "citation_style": "inline"
  }'
```

**Example response (abbreviated)**:
```json
{
  "session_id": "a3b1c2d4-...",
  "synthesis": "ABSTRACT\nLoRA and full fine-tuning represent two ends...\n\nMAIN FINDINGS\n...",
  "evaluation": {
    "coherence_score": 0.84,
    "relevance_score": 0.91,
    "factuality_score": 0.78,
    "completeness_score": 0.82,
    "composite_score": 0.848,
    "verdict": "PASS"
  },
  "pipeline_summary": {
    "total_tokens": 3180,
    "elapsed_ms": 7240,
    "agents_completed": ["researcher", "critic", "synthesizer", "validator"]
  }
}
```

---

## Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/synthesize` | Run full agent pipeline on a query |
| POST | `/api/v1/ingest` | Add a document to the corpus |
| POST | `/api/v1/query/corpus` | Semantic search over corpus |
| GET | `/api/v1/agents/status` | Agent configuration and corpus stats |
| POST | `/api/v1/agents/prompts/reload` | Hot-reload YAML prompt templates |
| GET | `/api/v1/analytics` | Session history, agent stats, cost summary |
| GET | `/health` | Health check |

---

## Configuration

Key `.env` settings:

```env
LLM_PROVIDER=openai           # or "ollama" for local
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

RETRIEVAL_TOP_K=6             # chunks passed to Researcher
ENABLE_CRITIC_AGENT=true      # set false to save tokens
ENABLE_VALIDATOR_AGENT=true
```

See [.env.example](.env.example) for all options.

---

## Testing

```bash
pytest tests/ -v

# By layer
pytest tests/unit/ -v          # no LLM calls, fast
pytest tests/integration/ -v   # mocked pipeline tests
pytest tests/evaluation/ -v    # metric correctness
```

---

## Docker

```bash
docker build -t synapseiq .
docker run -p 8000:8000 --env-file .env synapseiq
```

---

## Cost Reference

| Model | Cost per 1K queries (est.) |
|-------|--------------------------|
| gpt-4o-mini | ~$1.40 |
| llama3 (Ollama) | $0.00 |

---

## Documentation

Full project documentation (all 15 sections including architecture, evaluation framework, roadmap, cost analysis, and citations) is in:

**[docs/PROJECT_DOCUMENTATION.md](docs/PROJECT_DOCUMENTATION.md)**

---

## License

MIT
