# DocuMind: A Multi-Module AI Platform for Regulatory Intelligence and Knowledge Synthesis

**CS 599 — Contemporary Developments: Applications of Large Language Models**
Northern Arizona University · Department of Computer Science

---

## Project Title

**DocuMind — Production-Grade LLM Intelligence Platform for Document Understanding**
*Comprising: RegDelta (Regulatory Change Impact Analyzer) and SynapseIQ (Multi-Agent Research Intelligence Platform)*

---

## Abstract

Organizations operating in regulated industries generate and consume large volumes of structured documents daily. Two critical bottlenecks persist at enterprise scale: (1) compliance teams cannot efficiently propagate regulatory amendments across internal policy inventories, and (2) knowledge workers lack automated tools that synthesize multi-document corpora into rigorously evaluated artifacts. This project presents **DocuMind**, a production-grade AI platform comprising two complementary modules — **RegDelta** and **SynapseIQ** — both built on Retrieval-Augmented Generation (RAG) and Large Language Model (LLM) inference. RegDelta detects section-level regulatory changes, retrieves semantically matched internal policies from a vector store, and generates risk-classified impact reports via an LLM pipeline. SynapseIQ implements a four-agent sequential architecture (Researcher → Critic → Synthesizer → Validator) that produces self-evaluated knowledge syntheses with composite quality scoring. Both modules are deployed as production FastAPI services with ChromaDB vector stores, SQLite analytics databases, and Docker containerization. The platform demonstrates that LLMs, when combined with retrieval grounding and multi-agent oversight, can significantly reduce manual knowledge-work overhead in regulated domains.

---

## 1. Problem Statement

### 1.1 Regulatory Change Propagation

When regulatory bodies such as the SEC, FINRA, or Basel Committee amend rules, compliance teams at financial and healthcare institutions must manually cross-reference hundreds of internal policy documents to identify what requires updating. This process typically requires **2–4 weeks** per major amendment, is highly error-prone under deadline pressure, and produces no systematic audit trail linking identified policy gaps to specific changed regulatory clauses. The problem scales linearly with the size of both the regulation corpus and the organization's internal policy inventory.

### 1.2 Research and Knowledge Synthesis

Analysts, legal professionals, and researchers spend the majority of their cognitive effort reading, extracting, and manually integrating information from heterogeneous document corpora into coherent reports. Existing LLM-based tools — document summarizers and Q&A chatbots — retrieve relevant text but do not: (a) reason about logical gaps and contradictions across multiple sources, (b) apply structured critique before final synthesis, (c) self-evaluate output quality before delivery, or (d) maintain a traceable reasoning chain from raw source documents to the final artifact.

### 1.3 Why Existing Approaches Fall Short

| Approach | Limitation |
|----------|------------|
| Simple RAG chatbots | Returns raw chunks; no synthesized analysis; no quality gate |
| Document summarizers | Single-document scope; no cross-document reasoning |
| Manual compliance review | Non-scalable; no systematic gap detection; no audit trail |
| Generic LLM API calls | No domain retrieval; hallucination risk without grounding evidence |
| Rule-based diff tools | No semantic understanding of regulatory significance |

---

## 2. Objectives

### Module I — RegDelta

| ID | Objective | Success Criterion |
|----|-----------|-------------------|
| M1 | Section-level change detection | Diff two regulation versions at heading-level granularity with `ADDED`, `MODIFIED`, `REMOVED`, `UNCHANGED` classification |
| M2 | Semantic policy impact retrieval | Retrieve affected internal policies with cosine similarity ≥ 0.35 using dense vector search |
| M3 | LLM-generated impact report | Report includes `risk_level`, `executive_summary`, `affected_policies` list, and `recommended_actions` |
| M4 | Version registry | SQLite tracks all ingested regulation versions and generated reports with full metadata and timestamps |
| M5 | Production REST API | FastAPI endpoints with OpenAPI documentation, Pydantic validation, structured JSON logging, and health check |

### Module II — SynapseIQ

| ID | Objective | Success Criterion |
|----|-----------|-------------------|
| S1 | 4-agent sequential pipeline | Researcher → Critic → Synthesizer → Validator execute with shared `AgentContext` state object |
| S2 | Self-evaluating output | 4-dimension composite quality score computed before response delivery; `PASS`/`CONDITIONAL_PASS`/`FAIL` verdict issued |
| S3 | Format-adaptive synthesis | Generates `brief` (~300w), `standard` (~800w), and `detailed` (~2000w) knowledge artifacts correctly |
| S4 | Agent observability | Per-agent token count, latency (ms), and success status recorded per session in SQLite |
| S5 | Cost-bounded inference | Per-agent token budgets enforced; estimated USD cost tracked per query |

### Shared Platform Objectives

| ID | Objective | Success Criterion |
|----|-----------|-------------------|
| P1 | Swappable LLM backend | System operates identically with OpenAI API (`gpt-4o-mini`) or local Ollama instance (`llama3`) |
| P2 | Persistent vector store | ChromaDB retains embeddings across server restarts without re-ingestion |
| P3 | Containerized deployment | Docker build succeeds; embedding model pre-fetched at build time |
| P4 | Testable architecture | `pytest` suite covers unit, integration, and evaluation layers for both modules |

---

## 3. Methodology

### 3.1 Retrieval-Augmented Generation (RAG)

Both modules ground all LLM inference in retrieved document evidence rather than relying on parametric (training-time) knowledge. The RAG pipeline operates in two phases:

**Offline Indexing:** Raw documents (PDF, TXT, Markdown) are parsed, cleaned, and split into overlapping fixed-size chunks (512–800 tokens, 50–100 token overlap). Each chunk is embedded using `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional, L2-normalized dense vectors) and upserted into ChromaDB with SHA-256-based document IDs for idempotent re-ingestion.

**Online Retrieval:** At query time, the user's query is embedded with the same model and passed to ChromaDB's HNSW index for approximate nearest-neighbor search. The top-K (configurable, default 6–8) chunks above a minimum relevance threshold are returned as the grounding context for LLM generation.

### 3.2 Section-Level Differential Analysis (RegDelta)

RegDelta implements a domain-specific diff engine that operates at heading-level document granularity. Documents are parsed using a regex pattern matching standard regulatory heading conventions (`Section`, `Article`, `Rule`, `§` prefixes). Python's `difflib.SequenceMatcher` computes a similarity ratio (0.0–1.0) for each matched section pair. Sections are classified as `ADDED` (absent in old version), `REMOVED` (absent in new version), or `MODIFIED` (similarity < 1.0), and sorted by ascending similarity to surface the most significant changes first. The top 10 changed sections are individually annotated by the LLM with a one-sentence significance note before full impact report generation.

### 3.3 Multi-Agent Sequential Architecture (SynapseIQ)

SynapseIQ implements a four-stage sequential agent pipeline, all sharing an `AgentContext` dataclass that acts as a mutable state graph:

1. **ResearcherAgent** — Receives retrieved chunks and query; extracts structured findings, key concepts, and evidence gaps. Uses YAML+Jinja2 templated system/user prompts with a 1,200-token budget.
2. **CriticAgent** — Receives researcher output; identifies logical gaps, unsupported claims, and bias signals. Outputs structured JSON critique. 800-token budget.
3. **SynthesizerAgent** — Integrates findings and critique into a format-appropriate knowledge artifact (brief/standard/detailed). 1,800-token budget.
4. **ValidatorAgent** — Scores synthesis on four dimensions (coherence, relevance, factuality, completeness) using a weighted formula; issues a `PASS`/`CONDITIONAL_PASS`/`FAIL` verdict. 600-token budget.

All agents inherit from `BaseAgent`, which provides `_timed_llm_call()` (returns content, token count, and latency) and `_safe_run()` (with retry logic and graceful degradation on failure).

### 3.4 Evaluation Framework

**RegDelta** uses risk-level classification (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) determined by the LLM based on regulatory significance and affected policy count.

**SynapseIQ** uses a weighted composite evaluation score:

```
Composite = 0.30 × coherence + 0.35 × relevance + 0.25 × factuality + 0.10 × completeness
```

The `PipelineEvaluator` prefers LLM-generated scores from the ValidatorAgent; if the validator is disabled or fails, heuristic fallbacks are applied:
- **Coherence**: structural section detection (heading/paragraph pattern matching)
- **Relevance**: lexical overlap between query terms and synthesis text
- **Completeness**: length ratio relative to expected output format length

---

## 4. System Architecture

### 4.1 High-Level Architecture

```
                         ┌─────────────────────────────────┐
                         │      CLIENT LAYER                │
                         │  HTTP · Swagger UI · SDK         │
                         └──────────────┬──────────────────┘
                                        │ REST / JSON
                         ┌──────────────▼──────────────────┐
                         │      FastAPI Gateway             │
                         │  ASGI · Pydantic · OpenAPI 3.0  │
                         └──────┬───────────────┬──────────┘
                                │               │
              ┌─────────────────▼───┐     ┌─────▼──────────────────┐
              │  MODULE I           │     │  MODULE II              │
              │  RegDelta           │     │  SynapseIQ              │
              │                     │     │                         │
              │  DiffEngine         │     │  SynapseOrchestrator    │
              │  ImpactAnalyzer     │     │  Researcher → Critic    │
              │  VectorStore        │     │  Synthesizer → Validator│
              │  VersionTracker     │     │  PromptEngine           │
              └────────┬────────────┘     └────────────┬────────────┘
                       │                               │
              ┌─────────▼───────────────────────────────▼──────────┐
              │              SHARED INFRASTRUCTURE                  │
              │  ChromaDB · Embedding · LLMClient · Config · Logs  │
              └──────────┬──────────────────────────┬──────────────┘
                         │                          │
              ┌───────────▼──────────┐   ┌──────────▼───────────────┐
              │  SQLite (RegDelta)   │   │  OpenAI / Ollama LLM API │
              │  SQLite (SynapseIQ) │   │  all-MiniLM-L6-v2 Embed  │
              └──────────────────────┘   └──────────────────────────┘
```

### 4.2 RegDelta Data Flow

```
POST /api/v1/analyze/delta
    → fetch old/new regulation text (VersionTracker)
    → compute_section_diffs(old, new)  [difflib]
    → annotate each changed section    [LLM, 1-sentence]
    → embed changed section text       [MiniLM]
    → query policies ChromaDB collection
    → generate_impact_report(sections, policies) [LLM, JSON]
    → save_report(report_id, ...)      [SQLite]
    → return ImpactReport JSON
```

### 4.3 SynapseIQ Pipeline Flow

```
POST /api/v1/synthesize
    → ChromaDB vector search (top_k chunks)
    → ResearcherAgent: extract findings [YAML prompt → LLM]
    → CriticAgent: identify gaps        [YAML prompt → LLM]
    → SynthesizerAgent: draft artifact  [YAML prompt → LLM]
    → ValidatorAgent: score dimensions  [YAML prompt → LLM]
    → PipelineEvaluator: composite score
    → PipelineTracer: record to SQLite
    → return SynthesisResponse JSON
```

---

## 5. Technologies Used

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| Language | Python | 3.11+ | Primary implementation |
| Web Framework | FastAPI + Uvicorn | 0.110 | ASGI REST API server |
| LLM Provider | OpenAI gpt-4o-mini | — | Inference for all agents |
| LLM Provider (alt) | Ollama llama3 | — | Local inference option |
| Vector Database | ChromaDB | 0.5 | Dense vector storage and ANN search |
| Embedding Model | sentence-transformers all-MiniLM-L6-v2 | — | 384-dim text embeddings |
| Persistence | SQLite3 | — | Version tracking, session analytics |
| Data Validation | Pydantic v2 + pydantic-settings | — | Request/response models, settings |
| Prompt Templating | Jinja2 + YAML | — | Agent prompt management and hot-reload |
| Diff Engine | difflib (stdlib) | — | Section-level text comparison |
| Containerization | Docker | — | Deployment packaging |
| Testing | pytest | — | Unit, integration, evaluation tests |
| CI/CD | GitHub Actions | — | Automated test execution |

---

## 6. Role of Large Language Models

LLMs are the reasoning core of DocuMind. Critically, both modules use LLMs as **grounded reasoners** — every LLM call is supplied with retrieved document context, preventing hallucination and ensuring factual consistency.

### 6.1 LLM Usage in RegDelta

| Task | LLM Call | Input | Output |
|------|----------|-------|--------|
| Section significance annotation | Per changed section (≤10) | Old + new text excerpt, system prompt | One-sentence significance note |
| Full impact report generation | Once per analysis | All changed sections + matched policy excerpts | Structured JSON: risk_level, executive_summary, recommended_actions, policy_actions |

### 6.2 LLM Usage in SynapseIQ

| Agent | Task | Token Budget | Output Format |
|-------|------|-------------|---------------|
| ResearcherAgent | Extract structured findings from retrieved chunks | 1,200 | Sections: core_findings, key_concepts, evidence_gaps |
| CriticAgent | Identify logical gaps, unsupported claims, bias | 800 | Structured JSON critique |
| SynthesizerAgent | Produce knowledge artifact at specified format | 1,800 | Formatted document (brief/standard/detailed) |
| ValidatorAgent | Score synthesis on 4 dimensions; issue verdict | 600 | JSON scores + PASS/CONDITIONAL_PASS/FAIL |

### 6.3 Prompt Engineering Strategy

SynapseIQ uses a **YAML + Jinja2** prompt engineering system. Each agent's prompts are stored in versioned YAML files (`templates/researcher.yaml`, etc.) containing `version`, `system`, `user` (Jinja2 template), and `output_schema` fields. The `PromptEngine` class loads all templates at server startup and supports hot-reload via `POST /api/v1/agents/prompts/reload`, enabling prompt iteration without server restart.

### 6.4 Cost Control

- Per-agent token budgets are enforced in `constants.py` (`AGENT_TOKEN_BUDGETS`)
- All LLM calls record input and output token counts
- Cost is estimated using model pricing: `$0.00015/1K input`, `$0.00060/1K output` (gpt-4o-mini)
- A `CostReport` is included in every `/analytics` response
- Ollama local inference is available as a zero-cost alternative for development

---

## 7. Expected Outcomes

1. **Automated regulatory compliance gap detection** — RegDelta reduces manual policy review time from weeks to minutes by automatically identifying which internal policies are semantically affected by regulation amendments.

2. **Rigorous multi-source knowledge synthesis** — SynapseIQ produces quality-evaluated knowledge artifacts from multi-document corpora, with a traceable agent reasoning chain and a self-issued quality verdict before delivery.

3. **Production-grade system design** — Both modules demonstrate enterprise-quality software engineering: typed Python, dependency injection, structured logging, persistent storage, containerization, and comprehensive test coverage.

4. **Transferable RAG + Multi-Agent pattern** — The architectural patterns — dual-corpus RAG, section-level diff, sequential agent state sharing, YAML prompt management — are domain-agnostic and transferable to legal, medical, and scientific literature domains.

5. **Observable LLM inference** — Per-session agent traces, token counts, latency measurements, and cost estimates provide full observability into LLM usage, enabling optimization and debugging.

---

## 8. Timeline

| Phase | Duration | Deliverables |
|-------|----------|-------------|
| Phase 1 — Infrastructure | Week 1 | ChromaDB setup, FastAPI skeleton, embedding pipeline, SQLite schema |
| Phase 2 — RegDelta Core | Week 2 | DiffEngine, ImpactAnalyzer, VectorStore, VersionTracker, REST API |
| Phase 3 — SynapseIQ Core | Week 3 | All 4 agents, AgentContext, SynapseOrchestrator, PromptEngine |
| Phase 4 — Evaluation | Week 4 | PipelineEvaluator, metrics, cost tracker, analytics endpoints |
| Phase 5 — Testing & Docs | Week 5 | pytest suite (unit, integration, evaluation), README, proposal, diagrams |
| Phase 6 — Finalization | Week 6 | Docker, GitHub Actions CI, performance tuning, final documentation |

---

## 9. References

1. Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS 2020. arXiv:2005.11401.
2. Reimers, N., & Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks*. EMNLP 2019. arXiv:1908.10084.
3. OpenAI. (2024). *GPT-4o Technical Report*. openai.com/research/gpt-4o.
4. Chromadb. (2024). *ChromaDB: The AI-Native Open-Source Embedding Database*. github.com/chroma-core/chroma.
5. Yao, S., et al. (2023). *ReAct: Synergizing Reasoning and Acting in Language Models*. ICLR 2023. arXiv:2210.03629.
6. Wang, L., et al. (2024). *A Survey on Large Language Model based Autonomous Agents*. Frontiers of Computer Science. arXiv:2308.11432.
7. Peng, B., et al. (2023). *Check Your Facts and Try Again: Improving Large Language Models with External Knowledge and Automated Feedback*. arXiv:2302.12813.
8. Gao, Y., et al. (2024). *Retrieval-Augmented Generation for Large Language Models: A Survey*. arXiv:2312.10997.
9. FastAPI. (2024). *FastAPI Framework Documentation*. fastapi.tiangolo.com.
10. Chase, H. (2022). *LangChain: Building applications with LLMs*. github.com/langchain-ai/langchain.
