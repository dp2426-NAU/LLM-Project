# DocuMind — Full Technical Documentation

**CS 599 — Contemporary Developments: Applications of Large Language Models**
Version 1.0 | Northern Arizona University

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Design and Architecture](#2-system-design-and-architecture)
3. [Data Flow](#3-data-flow)
4. [Implementation Details](#4-implementation-details)
5. [Key Features](#5-key-features)
6. [Challenges and Solutions](#6-challenges-and-solutions)
7. [Evaluation and Results](#7-evaluation-and-results)
8. [Future Improvements](#8-future-improvements)

---

## 1. Project Overview

**DocuMind** is a production-grade AI platform that applies Large Language Models and Retrieval-Augmented Generation to two high-value document intelligence problems:

| Module | Name | Core Problem Solved |
|--------|------|---------------------|
| I | **RegDelta** | Detects how regulatory amendments affect internal compliance policies |
| II | **SynapseIQ** | Synthesizes multi-document corpora into rigorously quality-evaluated knowledge artifacts |

Both modules share a common infrastructure layer: FastAPI (ASGI), ChromaDB (vector store), sentence-transformers (embedding), SQLite (persistence), and a configurable LLM backend (OpenAI or Ollama).

### Key Properties

- **Grounded LLM inference** — every LLM call is supplied with retrieved document context; no hallucination from parametric memory
- **Production software quality** — Pydantic models, dependency injection, lifespan-managed services, structured JSON logging, Docker containerization
- **Observable pipelines** — per-agent token counts, latency measurements, cost estimates, and SQLite session traces
- **Swappable backends** — single `.env` flag switches between `openai` and `ollama` inference

---

## 2. System Design and Architecture

### 2.1 Repository Structure

```
LLM-Project/
├── README.md                     ← Unified platform documentation
├── docs/                         ← Academic deliverables and diagrams
│   ├── proposal.md
│   ├── documentation.md
│   ├── presentation.md
│   ├── demo_output.html
│   └── images/                   ← SVG architecture diagrams
├── RegDelta/                     ← Module I
│   ├── app/main.py               ← FastAPI factory + lifespan init
│   ├── app/config.py             ← Pydantic settings
│   ├── api/routes/               ← analyze.py, ingest.py, query.py
│   ├── models/impact_report.py   ← ImpactReport, RiskLevel, dataclasses
│   ├── rag/impact_analyzer.py    ← Main orchestration
│   ├── rag/retriever.py          ← ChromaDB semantic search
│   ├── rag/generator.py          ← LLM client (OpenAI / Ollama)
│   ├── store/vector_store.py     ← Dual-collection ChromaDB wrapper
│   ├── store/version_tracker.py  ← SQLite version and report registry
│   ├── ingestion/pipeline.py     ← Document ingestion orchestrator
│   ├── utils/diff_engine.py      ← Section-level diff with difflib
│   └── tests/                    ← 5 test modules
└── SynapseIQ/                    ← Module II
    ├── backend/main.py           ← FastAPI factory + lifespan init
    ├── backend/config/constants.py ← AgentRole, EVAL_WEIGHTS, budgets
    ├── backend/agents/           ← researcher, critic, synthesizer, validator
    ├── backend/pipeline/orchestrator.py ← SynapseOrchestrator
    ├── backend/prompts/engine.py ← YAML+Jinja2 PromptEngine
    ├── backend/prompts/templates/ ← 4 versioned YAML agent prompts
    ├── backend/evaluation/       ← PipelineEvaluator, metrics
    ├── backend/memory/           ← AgentContext, CorpusStore
    ├── backend/logging/          ← PipelineTracer, analytics
    ├── backend/utils/            ← cost_tracker, token_counter
    └── tests/                    ← unit/, integration/, evaluation/
```

### 2.2 Shared Infrastructure Layer

```
┌─────────────────────────────────────────────────────────────┐
│                   SHARED INFRASTRUCTURE                      │
│                                                             │
│  ┌─────────────────────┐   ┌────────────────────────────┐  │
│  │  ChromaDB           │   │  Embedding Engine           │  │
│  │  ./chroma_store/    │   │  all-MiniLM-L6-v2           │  │
│  │  HNSW ANN index     │   │  384-dim · L2 normalized    │  │
│  │  cosine metric      │   │  CPU · batch inference      │  │
│  └─────────────────────┘   └────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────┐   ┌────────────────────────────┐  │
│  │  LLM Client         │   │  Config (Pydantic)          │  │
│  │  OpenAI gpt-4o-mini │   │  BaseSettings + .env        │  │
│  │  Ollama llama3/local│   │  @lru_cache singleton       │  │
│  │  Retry + timeout    │   │  Environment override       │  │
│  └─────────────────────┘   └────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Module I — RegDelta Architecture

```
FastAPI (/api/v1/)
├── POST /ingest/regulation     → IngestionPipeline.ingest_regulation()
├── POST /ingest/policy         → IngestionPipeline.ingest_policy()
├── POST /analyze/delta         → ImpactAnalyzer.analyze()
├── GET  /reports/{report_id}   → VersionTracker.get_report()
├── GET  /regulations/{id}/versions → VersionTracker.get_versions()
├── POST /query/corpus          → Retriever.retrieve_regulations()
└── GET  /health
```

**Core orchestration in `ImpactAnalyzer.analyze()`:**
1. `compute_section_diffs(old_text, new_text)` → `list[SectionDiff]`
2. `_annotate_sections(diffs[:10])` → LLM per section → `list[ChangedSection]`
3. `Retriever.retrieve_policies(query)` → `list[dict]` per section
4. `LLMGenerator.generate_json(system, user)` → full `ImpactReport` JSON
5. `VersionTracker.save_report(...)` → SQLite persistence

### 2.4 Module II — SynapseIQ Architecture

```
FastAPI (/api/v1/)
├── POST /synthesize            → SynapseOrchestrator.run()
├── POST /ingest                → IngestionPipeline.ingest()
├── POST /query/corpus          → CorpusStore.search()
├── GET  /agents/status         → agent config + corpus stats
├── POST /agents/prompts/reload → PromptEngine.reload()
├── GET  /analytics             → PipelineTracer.get_cost_summary()
└── GET  /health
```

**Agent pipeline in `SynapseOrchestrator.run()`:**
1. `CorpusStore.search(query, top_k, min_score)` → `list[RetrievedChunk]`
2. `ResearcherAgent._safe_run(context)` → findings + key concepts
3. `CriticAgent._safe_run(context)` → gaps + unsupported claims (optional)
4. `SynthesizerAgent._safe_run(context)` → formatted knowledge artifact
5. `ValidatorAgent._safe_run(context)` → dimension scores + verdict
6. `PipelineTracer.end_session(...)` → SQLite analytics

---

## 3. Data Flow

### 3.1 Document Ingestion (Both Modules)

```
Input File (PDF / TXT / MD)
        │
        ▼
DocumentLoader.load(file_path)
   → extracts raw text
   → strips headers/footers
        │
        ▼
TextChunker.chunk(text, size=800, overlap=100)
   → fixed-size windows with overlap
   → generates SHA-256 doc_id per chunk
        │
        ▼
Embedder.embed(chunks)
   → all-MiniLM-L6-v2 batch inference
   → 384-dim L2-normalized float32 vectors
        │
        ▼
VectorStore.upsert(chunks, embeddings, metadata)
   → idempotent upsert into ChromaDB collection
   → metadata: source, chunk_id, doc_id, title, department
```

### 3.2 RegDelta — Regulatory Change Analysis

```
POST /api/v1/analyze/delta
{regulation_id, old_version_tag, new_version_tag}
        │
        ▼
VersionTracker.get_versions(regulation_id)
   → fetch old_text, new_text from SQLite
        │
        ▼
DiffEngine.compute_section_diffs(old_text, new_text)
   → regex split into {section_id: content} dicts
   → SequenceMatcher.ratio() per section pair
   → classify: ADDED | MODIFIED | REMOVED
   → sort by ascending similarity (most changed first)
        │
        ▼
ImpactAnalyzer._annotate_sections(diffs[:10])
   → LLM call per section:
     system: "regulatory compliance expert"
     user: old_excerpt + new_excerpt
     output: one-sentence significance note
        │
        ▼
Retriever.retrieve_policies(changed_section_text)
   → embed section text
   → ChromaDB.query(internal_policies, top_k=8)
   → deduplicate by policy_id (keep highest score)
        │
        ▼
LLMGenerator.generate_json(impact_system, impact_prompt)
   → system: "senior compliance officer"
   → user: changed_sections + matched_policies
   → output: {risk_level, executive_summary,
              recommended_actions, policy_actions}
        │
        ▼
ImpactReport(dataclass)
   → changed_sections: list[ChangedSection]
   → affected_policies: list[AffectedPolicy]
   → risk_level: RiskLevel enum
        │
        ▼
VersionTracker.save_report(report_id, ..., report_json)
   → persist to SQLite impact_reports table
        │
        ▼
Return ImpactReport.to_dict()  ← JSON response
```

### 3.3 SynapseIQ — Multi-Agent Pipeline

```
POST /api/v1/synthesize
{query, output_format, citation_style}
        │
        ▼
CorpusStore.search(query, top_k=6, min_score=0.35)
   → embed query with MiniLM
   → ChromaDB HNSW ANN search
   → filter by min relevance score
   → return list[RetrievedChunk]
        │
        ▼
AgentContext initialized:
   session_id, query, output_format, retrieved_chunks
        │
    ┌───▼──────────────────────────────────────────┐
    │  ResearcherAgent._safe_run(context)          │
    │  PromptEngine.render("researcher", ...)      │
    │  LLM: extract core_findings, key_concepts,   │
    │        evidence_gaps, source_quality_notes   │
    │  Tokens: ≤1,200 · Records to context        │
    └───┬──────────────────────────────────────────┘
        │
    ┌───▼──────────────────────────────────────────┐
    │  CriticAgent._safe_run(context)              │
    │  PromptEngine.render("critic", ...)          │
    │  LLM: gaps, unsupported_claims, bias_signals │
    │  Tokens: ≤800 · Optional (ENABLE_CRITIC)    │
    └───┬──────────────────────────────────────────┘
        │
    ┌───▼──────────────────────────────────────────┐
    │  SynthesizerAgent._safe_run(context)         │
    │  PromptEngine.render("synthesizer", ...)     │
    │  LLM: produce knowledge artifact             │
    │  Tokens: ≤1,800 · format=brief/standard/det │
    └───┬──────────────────────────────────────────┘
        │
    ┌───▼──────────────────────────────────────────┐
    │  ValidatorAgent._safe_run(context)           │
    │  PromptEngine.render("validator", ...)       │
    │  LLM: score coherence, relevance,            │
    │        factuality, completeness              │
    │  Compute composite = Σ(score_i × weight_i)  │
    │  Verdict: PASS ≥0.65 | COND ≥0.45 | FAIL   │
    └───┬──────────────────────────────────────────┘
        │
        ▼
PipelineEvaluator.evaluate(context)
   → EvaluationResult with all scores + verdict
        │
        ▼
PipelineTracer.end_session(session_id, context)
   → write to SQLite: pipeline_sessions, agent_traces
        │
        ▼
Return SynthesisResponse JSON
```

---

## 4. Implementation Details

### 4.1 DiffEngine (`RegDelta/utils/diff_engine.py`)

The section splitter uses a compiled regex to detect standard regulatory heading patterns:
```python
_SECTION_RE = re.compile(
    r"^(?:Section|SECTION|§|Article|ARTICLE|Rule|RULE)\s+[\d\.A-Z]+",
    re.MULTILINE,
)
```

If no headings are detected (e.g., unstructured text), the document falls back to 1,000-character fixed chunks labeled `chunk_0`, `chunk_1`, etc. This ensures the diff engine degrades gracefully.

The `SectionDiff` dataclass carries `section_id`, `title`, `old_text`, `new_text`, `change_type`, and `similarity` (rounded to 3 decimal places). Results are sorted by ascending similarity so the most structurally significant changes surface first.

### 4.2 Vector Store (`RegDelta/store/vector_store.py`)

RegDelta maintains two separate ChromaDB collections:
- `regulations` — for regulation version text chunks
- `internal_policies` — for internal compliance policy chunks

This dual-collection architecture prevents retrieval cross-contamination: policy queries only search the `internal_policies` collection, ensuring retrieved results are always organizational policies rather than regulation text.

### 4.3 Agent Base Class (`SynapseIQ/backend/agents/base.py`)

All agents inherit from `BaseAgent`, which provides:

- `_timed_llm_call(system, user)` → `(content: str, tokens: int, latency_ms: float)` — wraps LLM call with wall-clock timing
- `_safe_run(context)` → `AgentOutput` — catches exceptions, applies retry with exponential backoff, returns a failed `AgentOutput` on exhausted retries rather than raising
- `LLMClient` with `_openai_chat()` and `_ollama_chat()` backends selected by the `llm_provider` config field

### 4.4 Prompt Engine (`SynapseIQ/backend/prompts/engine.py`)

The `PromptEngine` loads all YAML templates at server startup. Each YAML file follows this schema:

```yaml
version: "1.2"
agent: researcher
system: |
  You are a rigorous research analyst...
user: |
  Query: {{ query }}
  Output format: {{ output_format }}
  Retrieved context:
  {% for chunk in retrieved_chunks %}
  [Source: {{ chunk.source }} | Score: {{ chunk.score }}]
  {{ chunk.text }}
  {% endfor %}
output_schema:
  core_findings: list[str]
  key_concepts: dict[str, str]
  evidence_gaps: list[str]
  source_quality_notes: str
```

The `render(agent_name, **kwargs)` method processes the Jinja2 template with the provided context variables and returns `(system_prompt, user_prompt)` tuple. `reload()` re-reads all YAML files from disk without server restart.

### 4.5 AgentContext (`SynapseIQ/backend/memory/context_graph.py`)

`AgentContext` is a shared mutable dataclass that all agents read from and write into:

```python
@dataclass
class AgentContext:
    session_id: str
    query: str
    output_format: str
    citation_style: str
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)
    research_output: Optional[AgentOutput] = None
    critique_output: Optional[AgentOutput] = None
    synthesis_output: Optional[AgentOutput] = None
    validation_output: Optional[AgentOutput] = None
    agent_outputs: list[AgentOutput] = field(default_factory=list)
    total_tokens: int = 0
    elapsed_ms: float = 0.0
    current_stage: PipelineStage = PipelineStage.INGESTION
```

`record_agent_output(output)` appends to `agent_outputs` and routes to the appropriate named attribute (`research_output`, `critique_output`, etc.) based on `output.stage`.

### 4.6 Evaluation Weights

```python
EVAL_WEIGHTS = {
    "coherence":    0.30,   # structural and logical consistency
    "relevance":    0.35,   # alignment with user query (highest weight)
    "factuality":   0.25,   # grounding in retrieved source documents
    "completeness": 0.10,   # coverage of query sub-topics
}
```

Verdict thresholds:
- `PASS` — composite ≥ 0.65
- `CONDITIONAL_PASS` — composite ≥ 0.45
- `FAIL` — composite < 0.45

### 4.7 SQLite Schema

**RegDelta (`regdelta_versions.db`)**:
```sql
CREATE TABLE regulation_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regulation_id TEXT NOT NULL,
    version_tag TEXT NOT NULL,
    text TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE impact_reports (
    report_id TEXT PRIMARY KEY,
    regulation_id TEXT NOT NULL,
    old_version TEXT NOT NULL,
    new_version TEXT NOT NULL,
    risk TEXT NOT NULL,
    report_json TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**SynapseIQ (`synapseiq.db`)**:
```sql
CREATE TABLE pipeline_sessions (
    session_id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    verdict TEXT,
    composite_score REAL,
    total_tokens INTEGER,
    elapsed_ms REAL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE agent_traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    stage TEXT NOT NULL,
    tokens_used INTEGER,
    latency_ms REAL,
    success INTEGER,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. Key Features

### 5.1 RegDelta Features

| Feature | Description |
|---------|-------------|
| Section-level diff | Detects ADDED, MODIFIED, REMOVED sections — not just character diffs |
| Semantic similarity scoring | SequenceMatcher ratio (0.0–1.0) quantifies degree of change per section |
| Dual-corpus retrieval | Separate ChromaDB collections for regulations and policies prevent cross-contamination |
| LLM section annotation | One-sentence significance note per changed section before full report |
| Risk classification | LLM assigns `low`, `medium`, `high`, or `critical` based on regulatory content and policy impact |
| Full audit trail | Every impact report saved to SQLite with regulation_id, versions, risk, and full JSON |
| Idempotent ingestion | SHA-256 document IDs allow safe re-ingestion without duplication |

### 5.2 SynapseIQ Features

| Feature | Description |
|---------|-------------|
| 4-agent pipeline | Sequential Researcher → Critic → Synthesizer → Validator with shared context |
| YAML prompt management | Versioned, hot-reloadable prompts with Jinja2 variable interpolation |
| Format-adaptive synthesis | `brief` (~300w), `standard` (~800w), `detailed` (~2000w) output modes |
| Self-evaluation | ValidatorAgent scores and issues verdict before response delivery |
| Token budget enforcement | Per-agent caps prevent runaway API costs |
| Cost tracking | Per-session USD cost estimated using model-specific pricing |
| Agent observability | Per-agent latency, token count, and success recorded per session |
| Heuristic fallback | If validator is disabled, heuristic metrics (lexical overlap, structural detection) replace LLM scores |

---

## 6. Challenges and Solutions

### Challenge 1 — Regulatory Document Structure Variability

**Problem:** Regulatory documents use inconsistent heading conventions (Section 1, ARTICLE II, § 3.4, Rule 17a-4). A single regex pattern cannot capture all formats.

**Solution:** The `DiffEngine` applies a broad compound regex matching multiple heading keywords. If no headings are detected at all (plain prose), it falls back to fixed 1,000-character chunks. This ensures the system handles both well-structured and unstructured regulations without failure.

### Challenge 2 — Cross-Document Policy Contamination

**Problem:** Storing regulations and policies in the same ChromaDB collection caused semantic bleed — policy queries sometimes retrieved regulation chunks instead of policy documents.

**Solution:** Implemented strict dual-collection isolation in `VectorStore`. The `regulations` collection and `internal_policies` collection are queried independently, with collection-level `where` filters applied at query time.

### Challenge 3 — Agent Failure Propagation

**Problem:** If one agent in the SynapseIQ pipeline raises an exception, it should not crash the entire pipeline or return an unhandled 500 error to the client.

**Solution:** `BaseAgent._safe_run()` wraps every agent call with try/except and exponential-backoff retry (configurable `max_retries`). On exhausted retries, it returns a `AgentOutput(success=False)` rather than raising. The orchestrator checks `output.success` and either skips optional agents or sets `context.current_stage = FAILED`.

### Challenge 4 — Prompt Iteration Without Downtime

**Problem:** Improving agent prompts during development requires server restart in most frameworks, creating a slow iteration loop.

**Solution:** `PromptEngine.reload()` re-reads all YAML files from disk and replaces the in-memory template cache. The API exposes `POST /api/v1/agents/prompts/reload` to trigger this without restart. Jinja2 template rendering is always called from the in-memory cache, so performance is unaffected during normal operation.

### Challenge 5 — LLM Evaluation Score Reliability

**Problem:** LLM-issued scores for coherence, relevance, factuality, and completeness can be inconsistent or biased (validators tend to score their own pipeline's output highly).

**Solution:** The `PipelineEvaluator` implements a two-tier evaluation strategy. LLM scores from `ValidatorAgent` are used when available. If the validator is disabled or fails, heuristic fallbacks provide objective measures: structural coherence via section-header detection, relevance via query-text Jaccard overlap, and completeness via length ratio against expected word count for the output format.

### Challenge 6 — Cost Control at Scale

**Problem:** Multi-agent pipelines with 4 LLM calls per query can accumulate significant API costs at scale.

**Solution:** Per-agent token budgets in `AGENT_TOKEN_BUDGETS` cap `max_tokens` on each LLM call. The `SessionCostTracker` accumulates token counts and computes USD cost estimates using `MODEL_PRICING`. Optional agents (`ENABLE_CRITIC_AGENT`, `ENABLE_VALIDATOR_AGENT`) can be disabled in `.env` for development or cost-sensitive deployments.

---

## 7. Evaluation and Results

### 7.1 System Performance Benchmarks (Estimated on gpt-4o-mini)

| Metric | RegDelta | SynapseIQ |
|--------|---------|-----------|
| End-to-end latency (typical) | 4–8 seconds | 6–12 seconds |
| Token consumption per query | ~2,000–3,500 | ~3,000–4,200 |
| Estimated cost per query | ~$0.003–0.005 | ~$0.004–0.007 |
| Vector retrieval latency | < 100ms | < 100ms |
| Embedding throughput | ~200 chunks/sec (CPU) | ~200 chunks/sec (CPU) |

### 7.2 SynapseIQ Evaluation Score Distribution (Sample)

| Dimension | Weight | Example Score | Weighted Contribution |
|-----------|--------|--------------|----------------------|
| Coherence | 0.30 | 0.84 | 0.252 |
| Relevance | 0.35 | 0.91 | 0.319 |
| Factuality | 0.25 | 0.78 | 0.195 |
| Completeness | 0.10 | 0.82 | 0.082 |
| **Composite** | **1.00** | — | **0.848 → PASS** |

### 7.3 RegDelta Risk Distribution (Sample Regulation Pair)

| Changed Sections | Risk Level | Affected Policies |
|-----------------|-----------|-------------------|
| 3 MODIFIED, 1 ADDED | HIGH | 4 policies |
| 2 MODIFIED | MEDIUM | 2 policies |
| 1 MODIFIED (minor) | LOW | 1 policy |

### 7.4 Test Coverage

| Module | Test Type | Files | Status |
|--------|-----------|-------|--------|
| RegDelta | Unit | test_ingestion.py | ✓ |
| RegDelta | Integration | test_api.py, test_rag.py | ✓ |
| SynapseIQ | Unit | test_agents.py, test_prompts.py | ✓ |
| SynapseIQ | Integration | test_pipeline.py | ✓ |
| SynapseIQ | Evaluation | test_metrics.py | ✓ |

---

## 8. Future Improvements

### Short-Term (v1.1)

| Improvement | Description |
|-------------|-------------|
| Streaming responses | WebSocket or Server-Sent Events for real-time agent progress |
| Streamlit dashboard | Visual UI for non-technical compliance users |
| PDF parsing hardening | Handle multi-column, table-heavy regulatory PDF layouts |
| Parallel agent execution | Run Researcher and Critic concurrently where safe (reduce latency by ~30%) |

### Medium-Term (v2.0)

| Improvement | Description |
|-------------|-------------|
| Multi-tenant support | Per-organization corpus isolation with authentication |
| Fine-tuned embeddings | Domain-specific embeddings trained on regulatory and legal corpora |
| Regulation change alerts | Scheduled ingestion from SEC EDGAR, Federal Register APIs with automated diff |
| Agent memory | Persistent long-term memory allowing agents to reference prior sessions |

### Long-Term Research Directions

| Direction | Description |
|-----------|-------------|
| LLM-as-judge calibration | Study validator bias; compare LLM scores to human expert ratings |
| Multi-modal documents | Handle scanned PDFs, charts, and tables in regulatory filings |
| Graph-based retrieval | Replace flat vector search with knowledge graph traversal for relational regulatory concepts |
| Cross-lingual support | Extend to EU regulatory documents (GDPR, MiFID II) in multiple languages |
