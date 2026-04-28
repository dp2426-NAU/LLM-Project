# DocuMind — Academic Documentation Index

**CS 599 — Contemporary Developments: Applications of Large Language Models**
Northern Arizona University

---

## What Is This Folder?

This `docs/` folder contains all academic deliverables for the DocuMind project, plus architecture diagrams and a live demo output page.

---

## File Index

| File | Type | Description |
|------|------|-------------|
| [proposal.md](proposal.md) | Academic Proposal | Formal project proposal: abstract, problem statement, objectives, methodology, architecture, LLM usage, references (PDF-ready) |
| [documentation.md](documentation.md) | Technical Documentation | Full system documentation: architecture, data flow, implementation details, challenges, evaluation, future work |
| [presentation.md](presentation.md) | Presentation Script | Slide-by-slide content (11 slides) with bullet points and speaker notes — convert to PPTX or Google Slides |
| [demo_output.html](demo_output.html) | Live Demo | Opens in browser to show real sample API outputs from both RegDelta and SynapseIQ — no server required |
| [images/](images/) | Diagrams | SVG architecture diagrams (GitHub-rendered inline) |

---

## Architecture Diagrams (`images/`)

| File | Description |
|------|-------------|
| [system_architecture.svg](images/system_architecture.svg) | Full 5-layer platform architecture: Client → API → Modules → Infra → Persistence |
| [agentic_workflow.svg](images/agentic_workflow.svg) | SynapseIQ 4-agent pipeline with token budgets, AgentContext, and evaluator |
| [regdelta_pipeline.svg](images/regdelta_pipeline.svg) | RegDelta end-to-end: ingestion → diff → LLM annotation → impact report |
| [rag_flow.svg](images/rag_flow.svg) | RAG mechanism: offline indexing phases + online query + grounded generation |

---

## How to View the Demo Output

Open this link in your browser (no setup required):

**[https://htmlpreview.github.io/?https://github.com/dp2426-NAU/LLM-Project/blob/main/docs/demo_output.html](https://htmlpreview.github.io/?https://github.com/dp2426-NAU/LLM-Project/blob/main/docs/demo_output.html)**

This page shows realistic sample JSON responses from both modules — what the API actually returns when you run a synthesis or regulatory analysis.

---

## How to Convert proposal.md → PDF

**Option A — Pandoc (recommended):**
```bash
pip install pandoc
pandoc docs/proposal.md -o DocuMind_Proposal.pdf \
  --pdf-engine=wkhtmltopdf \
  --variable margin-top=1in \
  --variable margin-bottom=1in \
  --variable margin-left=1in \
  --variable margin-right=1in
```

**Option B — VS Code:**
1. Install extension: "Markdown PDF" by yzane
2. Open `proposal.md` → right-click → "Markdown PDF: Export (pdf)"

**Option C — Online:**
1. Copy content of `proposal.md`
2. Paste into [https://dillinger.io](https://dillinger.io)
3. Export → PDF

---

## How to Convert presentation.md → PowerPoint

**Option A — Pandoc:**
```bash
pandoc docs/presentation.md -o DocuMind_Presentation.pptx
```

**Option B — Manual (Google Slides):**
1. Open Google Slides → New blank presentation
2. For each `## Slide N` section:
   - Create a new slide
   - Set the slide title from the `**Title:**` field
   - Add bullet points from the list items
3. Recommended theme: Dark background (`#0d1117`), white text, blue/green accents
4. Insert SVG diagrams from `docs/images/` into slides 5, 6, and 8

**Option C — Marp (Markdown → PPTX/PDF):**
```bash
npm install -g @marp-team/marp-cli
marp docs/presentation.md --pptx -o DocuMind_Slides.pptx
```

---

## Quick Reference — API Endpoints

### RegDelta (Module I)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/ingest/regulation` | Ingest a regulation document |
| POST | `/api/v1/ingest/policy` | Ingest an internal policy document |
| POST | `/api/v1/analyze/delta` | Run full change impact analysis |
| GET | `/api/v1/reports/{report_id}` | Retrieve a saved impact report |
| GET | `/health` | Health check |

### SynapseIQ (Module II)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/synthesize` | Run full 4-agent synthesis pipeline |
| POST | `/api/v1/ingest` | Add a document to the corpus |
| POST | `/api/v1/query/corpus` | Semantic search over corpus |
| GET | `/api/v1/agents/status` | Agent configuration and corpus stats |
| POST | `/api/v1/agents/prompts/reload` | Hot-reload YAML prompt templates |
| GET | `/api/v1/analytics` | Session history and cost summary |
| GET | `/health` | Health check |
