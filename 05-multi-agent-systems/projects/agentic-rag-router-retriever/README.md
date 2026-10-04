# Agentic RAG: Router–Retriever System with PDF and Web Search Tools

Course-end project — Alron Harry
Notebook: `Agentic_RAG_Router_Retriever.ipynb`

## 1. What it does

A multi-agent Retrieval-Augmented Generation system built with **CrewAI**. A user asks a question in plain language. A **Router Agent** decides where the answer should come from, and a **Retriever Agent** fetches evidence from that source and writes a grounded, cited answer.

| Source | Tool | Used for |
|---|---|---|
| Static PDF | `crewai_tools.PDFSearchTool` over *Attention Is All You Need* | Transformer architecture, attention, training details, BLEU results |
| Live web | LangChain `TavilySearchResults` | Recent, time-sensitive or out-of-scope facts |
| Direct LLM | none | Simple general knowledge that needs no retrieval |

## 2. System architecture

```
                 ┌──────────────────────┐
  user question ─▶   Router Agent       │  output_pydantic = RouteDecision
                 │  (no tools)          │  {route, reasoning, search_query, confidence}
                 └──────────┬───────────┘
                            ▼
                 ┌──────────────────────┐  equips the retriever with ONLY the chosen tool;
                 │  Orchestrator        │  keyword heuristic if routing output fails to parse
                 │  (AgenticRAG class)  │
                 └──────────┬───────────┘
              ┌─────────────┼──────────────┐
              ▼             ▼              ▼
        PDFSearchTool   Tavily web      no tool (LLM)
              └─────────────┼──────────────┘
                            ▼
                 ┌──────────────────────┐
                 │  Retriever Agent     │──▶ grounded answer + Sources
                 └──────────┬───────────┘
                            │ "INSUFFICIENT_EVIDENCE" on the PDF path
                            └──▶ orchestrator retries once with web search

  TraceLogger ◀── step_callback / task_callback / tool wrappers / orchestrator events
      └─▶ logs/trace.jsonl, logs/agentic_rag.log, CrewAI log files, swimlane charts
```

Components:

- **LLM:** `gpt-4o-mini` with temperature 0, so routing is deterministic. The model can be changed with the `RAG_MODEL` environment variable.
- **Tools:** both tools are wrapped in small CrewAI `BaseTool` classes (`transformer_paper_search`, `web_search`). The wrappers log every query and result, and format web results with their URLs.
- **Orchestrator:** the `AgenticRAG` class runs two single-agent crews in sequence and owns the branching, fallback and logging logic.
- **Tracing:** `TraceLogger` records structured events: `run_start`, `agent_step`, `tool_call`, `tool_result`, `task_complete`, `route_decision`, `fallback` and `run_end`.

## 3. Agents: logic and responsibilities

### Router Agent ("Query Router")
- **Input:** the raw user question.
- **Responsibility:** classify the question as `pdf`, `web` or `llm`. It also rewrites the question into a focused search query and gives a confidence score. It never answers the question itself.
- **Logic:** its backstory spells out what the PDF covers (architecture, training setup, results, authors). Recent or external topics go to `web`, and trivial general knowledge goes to `llm`.
- **Output:** a validated `RouteDecision` Pydantic object.

### Retriever Agent ("Retrieval Specialist")
- **Input:** the original question plus the router's route, reasoning and search query.
- **Responsibility:** call the assigned tool (at most two refinements), answer **only** from the retrieved evidence, and end with a *Sources* section listing paper passages or URLs.
- **Guardrail:** if the evidence does not answer the question, it replies `INSUFFICIENT_EVIDENCE` instead of making something up.
- **Tool enforcement:** a fresh retriever is created for each question and given only the routed tool. The router's decision is therefore enforced rather than merely suggested.

## 4. Coordination flow

1. `rag.ask(question)` starts a run and assigns it a `run_id`.
2. **Routing crew:** the Router Agent returns a `RouteDecision`. If parsing fails, a logged keyword heuristic takes over.
3. **Retrieval crew:** the orchestrator builds the Retriever Agent with the chosen tool and runs the retrieval task.
4. **Fallback:** if the PDF path returns `INSUFFICIENT_EVIDENCE`, the question is retried once on the web path. The route is recorded as `pdf→web`.
5. The answer, route, confidence and latency are stored, and the full trace is written to disk.

## 5. Traceability outputs

| File | Contents |
|---|---|
| `logs/trace.jsonl` | One JSON event per agent step, tool call or result, and decision |
| `logs/agentic_rag.log` | The same events in human-readable form |
| `logs/crew_router.log`, `logs/crew_retriever.log` | CrewAI's native execution logs |
| `logs/run_summary.csv` | One row per question: route, confidence, latency, router reasoning |
| `logs/swimlanes.png` | Timeline per run showing hand-offs Orchestrator → Router → Retriever → Tool |
| `logs/summary_charts.png` | Route distribution and events per agent |

## 6. Why CrewAI

- Its role, goal and backstory abstraction maps directly onto the Router and Retriever responsibilities.
- `PDFSearchTool` is native to CrewAI, and LangChain tools such as Tavily wrap cleanly.
- `output_pydantic` gives typed routing decisions.
- `step_callback`, `task_callback` and `output_log_file` provide tracing hooks out of the box.
- *LangGraph* allows finer graph control but needs more boilerplate for a two-agent pipeline. *AutoGen* is built around conversation, which makes strict tool enforcement harder.

## 7. Challenges and trade-offs

| Challenge | Decision / trade-off |
|---|---|
| A routing LLM can be wrong, or can return malformed output | Structured output with Pydantic, temperature 0, and a keyword-heuristic safety net. The heuristic is cruder, but it keeps the system from crashing. |
| An LLM agent may ignore the routed tool and pick another | The retriever only *has* the routed tool. The cost is a new agent per question, which is cheap. |
| Questions about the paper whose answer is not in it (for example, where the authors work today) | The router sends them to the web. If it misroutes, `INSUFFICIENT_EVIDENCE` triggers a web fallback. This adds latency and cost, but only on misses. |
| Hallucination | The answer must come only from the evidence, with mandatory sources and an explicit "insufficient evidence" exit. Answers may be shorter or more conservative as a result. |
| Two crews instead of one sequential crew | Python branching between the crews is explicit and easy to log. A single crew with task `context` would be more compact, but it is harder to enforce and inspect the route. |
| Cost and latency | At least two LLM calls per question (routing and answering), plus an embedding pass when the PDF is first indexed. `gpt-4o-mini` keeps this inexpensive. A single-agent design would be cheaper but less transparent. |
| Web results change over time | Web answers are not reproducible run to run. The URLs are logged so answers can be audited. |
| `TavilySearchResults` is deprecated in LangChain in favour of `langchain-tavily` | It is kept because the brief specifies it. Swapping it means changing one import inside `WebSearchTool`. |

## 8. How to run

1. Put `Agentic_RAG_Router_Retriever.ipynb` and `trasformer_research_paper-dataset.pdf` in the same folder.
2. Get an **OpenAI API key** (for the LLM and embeddings) and a **Tavily API key** (free tier at tavily.com).
3. Open the notebook in Jupyter and run all cells. You will be prompted for the keys, or you can set `OPENAI_API_KEY` and `TAVILY_API_KEY` beforehand.
4. Section 7.4 lets you ask your own questions. Section 8 shows traces and charts.

Requirements: Python 3.10–3.12, `crewai`, `crewai-tools`, `langchain-community`, `tavily-python`, `pandas`, `matplotlib` (installed by the first cell).
