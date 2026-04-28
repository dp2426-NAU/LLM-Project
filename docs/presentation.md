# DocuMind — Presentation Slides

**CS 599 — Contemporary Developments: Applications of Large Language Models**
Northern Arizona University

> **Format guide:** Each slide shows a title, bullet points, and speaker notes.
> Convert to PowerPoint using Pandoc: `pandoc presentation.md -o presentation.pptx`
> Or paste slide content into Google Slides / PowerPoint manually.

---

## Slide 1 — Title Slide

**Title:** DocuMind
**Subtitle:** A Production-Grade LLM Intelligence Platform for Regulatory Analysis and Knowledge Synthesis

**Course:** CS 599 — Contemporary Developments: Applications of Large Language Models
**Institution:** Northern Arizona University
**Module I:** RegDelta — Regulatory Change Impact Analyzer
**Module II:** SynapseIQ — Multi-Agent Research Intelligence Platform

> *[Insert: system_architecture.svg diagram as background or side visual]*

---

## Slide 2 — Introduction

**Title:** What is DocuMind?

- A unified AI platform built on **Large Language Models + Retrieval-Augmented Generation (RAG)**
- Two production-grade modules targeting high-value document intelligence problems in regulated industries
- Demonstrates enterprise-quality software engineering: typed Python, FastAPI, ChromaDB, Docker, pytest
- Both modules share a common infrastructure: vector store, embedding engine, LLM client, persistent analytics
- Open-source, self-hostable, supports both OpenAI API and local Ollama inference

**Speaker Notes:**
DocuMind is not a toy demo — it is designed to production standards with dependency injection, Pydantic validation, lifespan-managed services, and structured logging. Both modules are independently deployable and share infrastructure by design.

---

## Slide 3 — Problem Statement

**Title:** Two Unsolved Enterprise Knowledge-Work Problems

**Problem A — Regulatory Compliance Propagation:**
- When a regulation is amended, compliance teams manually review hundreds of internal policies
- Process takes **2–4 weeks** per amendment at mid-size firms
- Error-prone under deadline pressure; no systematic audit trail
- Scales linearly with policy inventory size

**Problem B — Research Synthesis at Scale:**
- Analysts spend most effort manually synthesizing multi-document corpora
- Simple RAG chatbots return chunks — they don't reason, critique, or self-evaluate
- No quality gate before delivering synthesized content to decision-makers
- No traceable reasoning chain from raw source to final artifact

> *[Visual: split problem/solution table from README Section 1]*

**Speaker Notes:**
Both problems are real enterprise bottlenecks. RegDelta addresses compliance propagation; SynapseIQ addresses research synthesis. Both rely on the same RAG foundation but apply it differently.

---

## Slide 4 — Solution Overview

**Title:** DocuMind Architecture — Two Specialized Modules

**Module I — RegDelta:**
- Detects section-level changes between regulation versions using `difflib.SequenceMatcher`
- Semantically retrieves affected internal policies from ChromaDB
- LLM generates risk-classified impact report (risk_level: LOW/MEDIUM/HIGH/CRITICAL)
- Full audit trail in SQLite: every version and report persisted

**Module II — SynapseIQ:**
- 4-agent sequential pipeline: Researcher → Critic → Synthesizer → Validator
- Each agent uses versioned YAML + Jinja2 prompt templates
- Composite quality score computed before response delivery
- PASS / CONDITIONAL_PASS / FAIL verdict issued automatically

**Shared Infrastructure:**
- ChromaDB vector store + `all-MiniLM-L6-v2` embeddings (384-dim)
- OpenAI `gpt-4o-mini` or local Ollama — single `.env` switch
- FastAPI + Pydantic + Docker + pytest

> *[Visual: docs/images/system_architecture.svg]*

---

## Slide 5 — Architecture Diagram

**Title:** System Architecture — 5-Layer Design

```
CLIENT LAYER      HTTP · Swagger UI · Python SDK · CI/CD
       ↓
API GATEWAY       FastAPI/Uvicorn ASGI · Pydantic · OpenAPI 3.0
       ↓
DOMAIN MODULES    RegDelta (Diff → Analyze → Report)
                  SynapseIQ (Researcher → Critic → Synthesizer → Validator)
       ↓
SHARED INFRA      ChromaDB · Embedding Engine · LLM Client · Config · Logs
       ↓
PERSISTENCE       SQLite (versions + reports) · SQLite (sessions + traces)
                  ChromaDB on disk · OpenAI API / Ollama local
```

**Key Design Decisions:**
- Dual-corpus ChromaDB prevents retrieval cross-contamination between regulation and policy text
- AgentContext dataclass acts as shared mutable state graph across all 4 SynapseIQ agents
- Lifespan context manager initializes services once at startup; injected via `request.app.state`

> *[Visual: docs/images/system_architecture.svg — embed as full-slide image]*

---

## Slide 6 — LLM Integration

**Title:** Where and How LLMs Are Used

**RegDelta LLM Calls:**
- **Section annotation** (1 call per changed section, ≤10 sections): one-sentence significance note
- **Impact report generation** (1 call): outputs `risk_level`, `executive_summary`, `recommended_actions`, `policy_actions` as JSON

**SynapseIQ LLM Calls (4 agents, 4 calls per query):**

| Agent | Task | Token Budget |
|-------|------|-------------|
| ResearcherAgent | Extract findings from retrieved chunks | 1,200 |
| CriticAgent | Identify gaps, bias, unsupported claims | 800 |
| SynthesizerAgent | Produce knowledge artifact (brief/standard/detailed) | 1,800 |
| ValidatorAgent | Score 4 dimensions; issue PASS/FAIL verdict | 600 |

**Prompt Engineering:**
- YAML + Jinja2 templating with version control
- Hot-reload via `POST /agents/prompts/reload` — no server restart needed
- All LLM calls grounded in retrieved document context — no hallucination from parametric memory

> *[Visual: docs/images/agentic_workflow.svg]*

---

## Slide 7 — Key Features

**Title:** Platform Capabilities

**RegDelta:**
- Section-level regulatory diff (ADDED / MODIFIED / REMOVED / UNCHANGED)
- Dual-corpus RAG: separate ChromaDB collections for regulations and policies
- LLM-annotated change significance per section
- Risk level classification: `low`, `medium`, `high`, `critical`
- SHA-256 idempotent document ingestion
- Full SQLite audit trail of all versions and impact reports

**SynapseIQ:**
- 4-agent sequential pipeline with shared `AgentContext` state
- Versioned YAML prompt templates with hot-reload
- Format-adaptive output: `brief` / `standard` / `detailed`
- Composite evaluation: `0.30×coherence + 0.35×relevance + 0.25×factuality + 0.10×completeness`
- Per-agent token budgets enforced programmatically
- Per-session USD cost estimation; heuristic fallback if validator disabled

**Shared:**
- Swappable LLM backend (OpenAI ↔ Ollama) via single env flag
- ChromaDB persistent vector store across restarts
- Docker containerization with pre-fetched embedding model

---

## Slide 8 — Demo Flow

**Title:** End-to-End Demo Walkthrough

**RegDelta Demo (4 steps):**
1. `POST /api/v1/ingest/regulation` — ingest SEC 17a-4 v2023 (old version)
2. `POST /api/v1/ingest/regulation` — ingest SEC 17a-4 v2024 (new version)
3. `POST /api/v1/ingest/policy` — ingest internal AML/KYC policy document
4. `POST /api/v1/analyze/delta` — triggers full pipeline; returns `ImpactReport` JSON with `risk_level: "high"`, changed sections, affected policies, and recommended actions

**SynapseIQ Demo (3 steps):**
1. `POST /api/v1/ingest` — ingest research corpus (transformers_overview.txt, llm_finetuning.txt)
2. `POST /api/v1/synthesize` — query: "Compare LoRA vs full fine-tuning for adapting LLMs", format: "standard"
3. Response: synthesis document + 4-dimension evaluation scorecard + `PASS` verdict + agent traces

**Demo Output Link:**
See live sample JSON outputs at: `docs/demo_output.html`

> *[Visual: docs/images/rag_flow.svg — show retrieval mechanism]*

---

## Slide 9 — Results and Impact

**Title:** Performance and Quality Outcomes

**Latency:**
- RegDelta end-to-end: **4–8 seconds** (including up to 10 LLM annotation calls)
- SynapseIQ end-to-end: **6–12 seconds** (4 sequential LLM calls)
- Vector retrieval: **< 100ms** per query

**Quality (SynapseIQ — sample run):**

| Dimension | Score |
|-----------|-------|
| Coherence | 0.84 |
| Relevance | 0.91 |
| Factuality | 0.78 |
| Completeness | 0.82 |
| **Composite** | **0.848 → PASS** |

**Cost (gpt-4o-mini):**
- RegDelta per analysis: **~$0.003–0.005**
- SynapseIQ per synthesis: **~$0.004–0.007**
- Ollama local inference: **$0.00** (no API cost)

**Engineering Quality:**
- 10 test modules across unit, integration, and evaluation layers
- 105+ Python source files across both modules
- Full OpenAPI documentation at `/api/v1/docs`

---

## Slide 10 — Future Work

**Title:** Roadmap and Open Research Questions

**Short-Term (v1.1):**
- Streaming responses via WebSocket for real-time agent progress visualization
- Streamlit dashboard UI for non-technical compliance users
- Parallel agent execution: Researcher + Critic concurrently (estimated 30% latency reduction)

**Medium-Term (v2.0):**
- Multi-tenant corpus isolation with authentication
- Automated regulatory change monitoring (SEC EDGAR, Federal Register API polling)
- Agent persistent memory across sessions
- Fine-tuned domain embeddings on regulatory and legal corpora

**Open Research Questions:**
- How calibrated are LLM self-evaluation scores vs. human expert ratings?
- Can graph-based retrieval outperform flat vector ANN search for relational regulatory concepts?
- What is the optimal agent decomposition for domain-specific synthesis tasks?

---

## Slide 11 — Conclusion

**Title:** Summary and Takeaways

**What was built:**
- A production-grade dual-module AI platform: RegDelta (regulatory impact analysis) + SynapseIQ (multi-agent research synthesis)
- Both modules demonstrate RAG as a practical grounding strategy — no hallucination, all outputs traceable to source documents

**What was demonstrated:**
- LLMs excel as **domain reasoners** when supplied with retrieved grounding context, not as standalone knowledge sources
- Multi-agent architectures with structured critique and self-evaluation improve output quality over single-shot generation
- Production LLM systems require: token budgets, cost tracking, observable pipelines, and graceful failure handling

**Key technical contributions:**
- Section-level regulatory diff engine with semantic LLM annotation
- 4-agent sequential pipeline with shared state and quality-gated delivery
- YAML+Jinja2 hot-reloadable prompt management system
- Dual-corpus ChromaDB architecture for isolated domain retrieval

**Repository:** [github.com/dp2426-NAU/LLM-Project](https://github.com/dp2426-NAU/LLM-Project)

---

## Conversion Instructions

### To PowerPoint:
```bash
pip install pandoc
pandoc presentation.md -o DocuMind_Presentation.pptx
```

### To Google Slides:
1. Open Google Slides → New Presentation
2. Copy each slide section's bullets into a new slide
3. Apply a professional dark theme (e.g., "Slate" or custom dark background)
4. Insert SVG diagrams from `docs/images/` into slides 5, 6, 8

### Recommended Slide Design:
- **Background**: Dark (#0d1117 or similar)
- **Primary text**: White (#e6edf3)
- **Accent color**: Blue (#388bfd) for RegDelta, Green (#3fb950) for SynapseIQ
- **Font**: Segoe UI or Inter, 28pt titles, 18pt body
