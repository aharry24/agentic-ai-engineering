# Agentic RAG: Router–Retriever with Claude, Docling and Local Embeddings

A two-agent Retrieval-Augmented Generation system built with **CrewAI** and **Anthropic Claude**. A **Router Agent** decides where each question should be answered from: a local research paper, live web search, or the model's own knowledge. A **Retriever Agent** then uses the matching tool and writes a source-cited answer.

The PDF pipeline is built step by step rather than hidden inside a single tool. Each stage can be inspected and swapped: **Docling** parsing → chunking → **local Hugging Face embeddings** → **ChromaDB** → a custom CrewAI tool.

**Notebook:** [`agentic_rag_anthropic.ipynb`](agentic_rag_anthropic.ipynb), saved with full outputs.

---

## Results

All four test questions were routed correctly in the saved run (Oct 2026, Google Colab, T4 GPU):

| # | Question | Expected | Routed to | Outcome | Time |
|---|---|---|---|---|---|
| 1 | How does multi-head attention work in the Transformer, and why use multiple heads? | `pdf_search` | `pdf_search` ✅ | Grounded explanation; the Retriever ran 5 refined searches of the paper | ~29 s |
| 2 | What are the latest breakthroughs in AI announced this week? | `web_search` | `web_search` ✅ | Summary of web results with sources | ~15 s |
| 3 | What is the capital of France? | `generate` | `generate` ✅ | Answered directly; no retrieval | ~6 s |
| 4 | What BLEU score did the Transformer achieve on English-to-German translation? | `pdf_search` | `pdf_search` ✅ | **28.4 BLEU** on WMT 2014 EN-DE, matching the paper | — |

Full answers are in [`outputs/agentic_rag_results.json`](outputs/agentic_rag_results.json), and the step-by-step trace is in [`outputs/agentic_rag_trace.log`](outputs/agentic_rag_trace.log).

---

## Architecture

```
User question
     │
     ▼
┌──────────────────────────────┐   knows the PDF's title + section headings
│ Router Agent (Claude)        │── rules applied in order:
│ → pdf_search | web_search    │     1. PDF covers the topic → pdf_search
│   | generate                 │     2. needs current info  → web_search
└──────────────┬───────────────┘     3. otherwise           → generate
               │ route label (passed as task context)
               ▼
┌──────────────────────────────┐
│ Retriever Agent (Claude)     │── pdf_search : Docling → chunks → MiniLM → Chroma
│ uses the routed tool, cites  │── web_search : Tavily
│ its source                   │── generate   : model knowledge
└──────────────┬───────────────┘
               ▼
     Answer + source, JSON results, trace log
```

| Component | Technology | Why |
|---|---|---|
| Agents and orchestration | CrewAI, `Process.sequential` | The Router's label is passed to the Retriever as task context |
| LLM | Claude Sonnet 4.5 | Shared by both agents |
| PDF parsing | Docling | Recognises layout (headings, tables, two-column reading order), so chunks follow real section boundaries |
| Chunking | `RecursiveCharacterTextSplitter` (1000 chars / 150 overlap) | Splits on Markdown headings first; the paper becomes 71 chunks |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (local) | No API key, no cost, no rate-limit failures during a demo |
| Vector store | ChromaDB (in-memory) | Explicit and easy to inspect |
| Web search | Tavily | Live results for time-sensitive questions |
| Tracing | Python `logging` → file + stdout | Records every route decision and tool query |

---

## Design decisions

**1. The Router is told what the PDF contains.** In the first version, the Router knew only that "a PDF" existed. Multi-head attention is a well-known topic, so it answered from memory (`generate`) instead of searching the document. The fix builds a short table of contents from Docling's section headings and gives it to the Router. A priority rule tells it to prefer the PDF whenever the PDF covers the topic, *even if it could answer from general knowledge*. Routing accuracy depends on the router knowing what each source contains, not just that the source exists.

**2. Local embeddings instead of a hosted API.** The original course notebook failed with an OpenAI `insufficient_quota` (429) error during embedding. Running MiniLM locally removes that failure. The trade-off is slightly lower embedding quality than large hosted models.

**3. An explicit pipeline instead of CrewAI's `PDFSearchTool`.** This takes more code, but each stage (parse, chunk, embed, store, search) can be inspected, tested and swapped on its own.

**4. Fixes for recent library changes:**
- **Async kickoff.** Recent CrewAI versions refuse a synchronous `crew.kickoff()` inside a notebook's running event loop, so the pipeline uses `await crew.kickoff_async()`.
- **No `temperature`.** The current Anthropic Python SDK no longer accepts a `temperature` argument, so the LLM is configured without one.
- **Logging.** `logging.basicConfig(..., force=True)` is needed because Colab sets up logging before the notebook runs, which otherwise makes `basicConfig` silently do nothing.
- **Route parsing.** The route label is extracted with a regex, so a reply like "Route: pdf_search." is still recorded correctly.

---

## Limitations and next steps

- **Web freshness isn't verified.** Asked for news from "this week", the web route returned articles several months old. A production version should filter results by date, or tell the user when nothing recent was found.
- **No automated evaluation yet.** Next step: a labelled set of about 20 questions to measure routing accuracy, plus answer-faithfulness checks.
- **Single document, in-memory index.** The index is rebuilt every session. A persistent Chroma store would let it scale to more documents.
- **No fallback route.** If the PDF has no answer, the system doesn't retry on the web. A PDF-to-web fallback (as in my [Router–Retriever course project](../../../05-multi-agent-systems/projects/agentic-rag-router-retriever)) would cover this.

---

## Run it

**Google Colab (recommended; a GPU speeds up Docling):**

1. Open the notebook in Colab.
2. Add `ANTHROPIC_API_KEY` and, for the web route, `TAVILY_API_KEY` under **Secrets** (🔑), with **Notebook access** turned on.
3. Upload `transformer_research_paper-dataset.pdf` to the Colab file browser.
4. Run the install cell, then **Runtime ▸ Restart session**, then run all cells from Section 2.

**Locally:**

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # and TAVILY_API_KEY for web search
jupyter notebook agentic_rag_anthropic.ipynb
```

## Files

```
agentic-rag-anthropic/
├── README.md
├── agentic_rag_anthropic.ipynb          # notebook with saved outputs
├── requirements.txt
├── transformer_research_paper-dataset.pdf
└── outputs/
    ├── agentic_rag_results.json         # question, route, answer, timestamp
    └── agentic_rag_trace.log            # full reasoning and tool trace
```

**Source document:** Vaswani et al., *Attention Is All You Need* (2017), [arXiv:1706.03762](https://arxiv.org/abs/1706.03762). It is included for reproducibility, with the attribution notice on its first page.
