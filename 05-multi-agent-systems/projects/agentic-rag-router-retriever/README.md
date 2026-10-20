# Agentic RAG: Router–Retriever System with PDF and Web Search Tools

**Course-end project** · Alron Harry

A multi-agent Retrieval-Augmented Generation system built with **CrewAI**. A **Router Agent** decides where each question should be answered from: the research paper *Attention Is All You Need* (PDF), the live web, or the LLM's own knowledge. A **Retriever Agent** then retrieves from that source only and writes an answer grounded in the evidence, with its sources.

**Notebook:** [`Agentic_RAG_Router_Retriever.ipynb`](Agentic_RAG_Router_Retriever.ipynb)

## System architecture

```
                     ┌──────────────────────────────┐
  User question ───▶ │ Router Agent                 │  knows the PDF's table of contents
                     │ → RouterJudgement            │  (extracted from the PDF in code)
                     │   time_sensitive ·           │
                     │   pdf_section · search_query │
                     │ → decide_route (code)        │
                     └──────────────┬───────────────┘
                                    ▼
                     ┌──────────────────────────────┐
                     │ Orchestrator (AgenticRAG)    │  gives the Retriever ONLY the routed tool
                     └──────────────┬───────────────┘
                 pdf ┌──────────────┼──────────────┐ llm
                     ▼              ▼ web          ▼
           PDFSearchTool     TavilySearchResults   no tool
           (crewai_tools)    (LangChain)
                     └──────────────┬──────────────┘
                                    ▼
                     ┌──────────────────────────────┐
                     │ Retriever Agent              │──▶ grounded answer + Sources
                     └──────────────┬───────────────┘
                                    │ INSUFFICIENT_EVIDENCE on the pdf route
                                    └──▶ orchestrator retries once on the web route

  Every step ──▶ TraceLogger ──▶ logs/trace.jsonl · logs/agentic_rag.log · swimlane charts
```

| Component | Technology |
|---|---|
| Agents and orchestration | CrewAI (`Agent`, `Task`, `Crew`, `Process.sequential`) |
| LLM | OpenAI `gpt-4o-mini` (configurable with `RAG_MODEL`) |
| PDF search | `crewai_tools.PDFSearchTool`: chunks, embeds and searches the paper |
| Web search | LangChain `TavilySearchResults` |
| Router's view of the PDF | Table of contents extracted with `pypdf` |
| Structured routing | Pydantic `RouterJudgement` via `output_pydantic`; rules applied in code by `decide_route` |
| Tracing | Custom `TraceLogger` fed by CrewAI `step_callback`, `task_callback` and the tool wrappers |
| Visualisation | pandas and matplotlib (swimlane timelines, route and event charts) |

## Logic and responsibilities of each agent

**Router Agent (`Query Router`)**
- **Responsibility:** decide where the answer lives. It never retrieves or answers.
- **Input:** the user's question. Its backstory contains the paper's title and its **table of contents, extracted from the PDF**.
- **Logic:** the Router makes two narrow **judgements**, and code applies the routing rules:
  - `time_sensitive`: could the correct answer today differ from the answer a year ago? (news, latest releases, prices, someone's current job)
  - `pdf_section`: which heading of the table of contents covers the question, copied exactly, or none.

  `decide_route` then applies three rules in order: time-sensitive → `web`; a real section named → `pdf` (**even if the model could answer from memory**); otherwise → `llm`. When a real section covers the topic, a time-sensitive judgement only wins if the question itself asks about the present ("today", "latest", "this year"…), so the paper's own fixed results stay on the PDF. The code also checks that the named section exists, so an invented section can't send a question to the PDF.

  The Router is given **today's date** only for writing its search query, so "this year" becomes the right year.
- **Output:** a validated `RouterJudgement` (both judgements, reasoning and a search query), which `decide_route` turns into a `RouteDecision`.

**Retriever Agent (`Retrieval Specialist`)**
- **Responsibility:** retrieve evidence from the routed source and write the answer.
- **Input:** the original question, the Router's decision and reasoning, and the optimised search query.
- **Logic:** it is created per question with **only the routed tool**, so it cannot use a different source. It may refine its search up to twice and answers only from the retrieved text.
- **Output:** a 2–6 sentence answer with a *Sources* section (paper sections or URLs), or `INSUFFICIENT_EVIDENCE` with what is missing.

**Orchestrator (`AgenticRAG`)**
- Runs the Router crew, then builds the Retriever with the chosen tool and runs the Retriever crew.
- If the Router's output can't be parsed, falls back to a keyword heuristic and logs it.
- If the PDF route returns `INSUFFICIENT_EVIDENCE`, retries once on the web route (`pdf→web`) and logs the fallback.

## Coordination flow

1. **Question in:** `await rag.ask(question)` starts a run with its own ID.
2. **Route:** the Router crew returns a `RouterJudgement` (logged as `router_judgement`), and `decide_route` turns it into a `RouteDecision` (logged as `route_decision`).
3. **Equip:** the orchestrator gives the Retriever Agent exactly one tool (or none for `llm`) and a task containing the question and the search query.
4. **Retrieve and answer:** the Retriever crew calls the tool; every query and result is logged by the tool wrappers.
5. **Fallback, if needed:** an insufficient PDF answer triggers one web retry.
6. **Answer out:** the final answer, route, timing and the Router's reasoning are returned and logged as `run_end`.

## Reasoning traceability

Every event is stored in memory, written to `logs/trace.jsonl` (machine-readable) and `logs/agentic_rag.log` (human-readable):

| Event | Logged by | Content |
|---|---|---|
| `run_start` / `run_end` | Orchestrator | the question; the final answer, route and time |
| `router_judgement` | Router Agent | the two judgements, reasoning, search query |
| `route_decision` | Router Agent (via `decide_route`) | route, reasoning, search query, matched section |
| `agent_step` | each agent (`step_callback`) | thoughts, tool choices, intermediate output |
| `tool_call` / `tool_result` | tool wrappers | the exact query and what came back |
| `task_complete` | each task (`task_callback`) | the task's output |
| `fallback`, `router_error` | Orchestrator | orchestration decisions and errors |

In the notebook, `explain_run` summarises each agent's contribution to a run, `print_run` lists every event in order, and swimlane charts show the hand-offs from Router to Retriever to tool over time. The crews' own logs are saved to `logs/crew_router.log` and `logs/crew_retriever.log`.

## Demo

The notebook runs questions on every route:

| Route | Example questions |
|---|---|
| `pdf` | BLEU score on WMT 2014 English-to-German; how multi-head attention works; the learning-rate schedule |
| `web` | the latest open-weight LLMs; where the paper's authors work today |
| `llm` | what RAG stands for |

A **routing check** (Section 7.5) runs the Router alone on 11 labelled questions and reports its accuracy. It includes well-known topics the paper covers, such as positional encodings, which a router without the table of contents tends to answer from memory.

## Results

From the final run:

| Measure | Result |
|---|---|
| Routing check (11 labelled questions) | **11/11** |
| Demo questions routed correctly | **6/6** |
| Every route demonstrated | `pdf` 3, `web` 2, `llm` 1 |
| Time per question | 2.6–10.0 s |

The routing check shows both of the Router's judgements for every question, so each route can be traced to the judgement behind it. The last two questions show the boundary between `pdf` and `web` working. The paper's own BLEU result was judged not time-sensitive and routed to `pdf` (section 6.1). Comparing that result with *today's* models was judged time-sensitive while also naming section 6.1; because the question asks about the present, the code sent it to `web`.

Example answers:

- **`pdf`:** the BLEU score on WMT 2014 English-to-German, routed to section 6.1 of the paper instead of the web.
- **`pdf`:** multi-head attention, answered from section 3.2.2: 8 parallel heads with d_k = d_v = 64 in the base model.
- **`pdf`, with a refined search:** the learning-rate schedule. The first search returned unrelated text, so the Retriever searched again and found section 5.3 (warm-up of 4,000 steps, then decay with the inverse square root of the step number).
- **`web`:** the latest open-weight models, searched as "… 2026" thanks to the date fix, where an earlier run had searched for 2023.
- **`llm`:** "What does RAG stand for?", answered directly in 2.5 s with no retrieval.

## Challenges faced and trade-offs made

**1. The Router didn't know what the PDF contained.** Told only that "a PDF exists", a router tends to answer famous topics such as attention from memory instead of retrieving from the paper, so the answer isn't grounded in the document. A hand-written description of the paper in the backstory helps, but it has to be rewritten for every document.
*Fix:* extract the table of contents from the PDF with `pypdf` and give it to the Router, with a rule to prefer the PDF whenever a section covers the topic. Headings are accepted only if their section numbers increase, which filters out table rows and references.
*Trade-off:* the heading rules suit numbered academic papers. A PDF without numbered headings would need a layout-aware parser such as Docling.

**2. Questions that mention the paper but need current facts.** "Where do the authors work today?" names the paper, but the paper can't answer it.
*Fix:* the time-sensitive `web` rule is applied before the `pdf` rule, as long as the question itself asks about the present (see challenge 3).

**3. The first full run found two routing bugs, both visible in the logs.**
- *The direct-LLM route was never used.* The first version of the `web` rule said "information from after the paper, or current facts". The Router read that broadly: it sent "what is the capital of France?" to the web as a "current fact", and "what does RAG stand for?" to the web because RAG postdates 2017. The routing check scored 7/8, and no demo question took the `llm` route.
- *Stale search queries.* Asked for models released "this year", the Router wrote a search query for **2023**, its training-data year, so the answer listed 2023 models as the latest.

*First fix (prompt):* the `web` rule was reworded to depend on whether the answer is **time-sensitive**, the `llm` rule named stable facts and acronyms, both agents were given today's date, and a RAG-definition case was added to the routing check. The routing check scored **7/9**: still two `llm` questions sent to the web. The Router's own reasoning showed why. For "What is the capital of France?" it wrote that the fact is stable, "but since it is asked in the context of 'this year'… the web is the appropriate source". The question says nothing about this year; the phrase came from the date instruction in the prompt. Rewording rules wasn't making a small model apply them reliably.

*Second fix (code):* the LLM no longer picks the route. It answers two narrow questions (is the answer time-sensitive? which section covers it?) and `decide_route` applies the rules in code, the same way every time. The date now appears only in the instruction for writing the search query. The routing check's table shows both judgements for every question, so a wrong route can be traced to the judgement that caused it. The example in the prompt is deliberately not one of the test questions.

*Result:* the routing check scored **9/9**, and every judgement was visible in its table. But one demo question still went wrong: for "What BLEU score did the Transformer achieve on WMT 2014?", the Router correctly named section 6.1, yet judged the question time-sensitive because "the result could change with new models". A score the paper reported is fixed, so the answer came from the web instead of the document.

*Third fix (code tie-breaker):* when a real section covers the topic, a time-sensitive judgement only wins if the question itself asks about the present ("today", "latest", "this year"…). The judgement's definition now says that results reported in a fixed document are not time-sensitive. Two cases were added to the routing check: the BLEU question (→ `pdf`) and a comparison with *today's* models (→ `web`).

*Final result:* **11/11** on the routing check and **6/6** demo questions routed correctly, with every route used (see Results).

*Lesson:* LLMs are better at narrow judgements than at applying a list of ordered rules. Put the judgements in the model and the rules in code, check the judgements against what the question actually says, and turn every failure you find into a test case.

**4. Making the routing decision binding.** If the Retriever had both tools, it could ignore the Router.
*Fix:* the Retriever is created per question with only the routed tool.
*Trade-off:* a new agent and crew per question adds some overhead.

**5. Unreliable free-text routing.** Parsing a label out of prose is fragile.
*Fix:* `output_pydantic=RouterJudgement` validates the Router's output, and a logged keyword heuristic takes over if parsing fails.

**6. Questions the paper can't answer.** A wrong `pdf` route would otherwise produce a weak answer.
*Fix:* the Retriever must reply `INSUFFICIENT_EVIDENCE` rather than guess, and the orchestrator retries once on the web.
*Trade-off:* a fallback run costs a second retrieval.

**7. Library changes.** Recent CrewAI versions refuse a synchronous `kickoff()` inside the event loop Jupyter and Colab run, so the crews use `kickoff_async()`. CrewAI's interactive "view your execution traces?" prompt can pause a run, so tracing is turned off. `TavilySearchResults` is deprecated in LangChain in favour of `langchain-tavily`, but it is kept because the project brief requires it.

**8. Framework choice: CrewAI.** Its role/goal/backstory model maps directly onto the two agents, `PDFSearchTool` ships with `crewai_tools`, `output_pydantic` gives typed, validated Router output, and its callbacks provide the hooks for tracing. LangGraph would give finer control over the flow but needs more code for a two-step pipeline; AutoGen's conversation-centric design makes "use only the routed tool" harder to enforce.
*Trade-off:* `PDFSearchTool` hides its chunking and embedding settings, which is simpler but harder to tune or inspect than a hand-built pipeline.

**9. A confidence score that measured nothing.** The Router originally reported a confidence (0–1) for each decision. It was 0.9 on almost every question, including both wrong routes (the BLEU question sent to the web scored 0.9; "capital of France" sent to the web scored 1.0). A number the model writes about its own certainty isn't a measurement, so it was removed rather than shown as if it meant something.

**10. Cost and latency.** Each question makes at least two LLM calls (routing, then retrieval). A small model (`gpt-4o-mini`) keeps this cheap; the Router could later be replaced by a cheaper classifier for obvious cases.

## Run it

1. Open the notebook in Google Colab, or Jupyter.
2. Add `OPENAI_API_KEY` and `TAVILY_API_KEY`. In Colab, use **Secrets** (🔑) with notebook access on; elsewhere, set environment variables or enter them when prompted.
3. Put `transformer_research_paper-dataset.pdf` next to the notebook.
4. Run the install cell, restart the kernel if prompted, then run all cells.

Outputs are written to `logs/`: `trace.jsonl`, `agentic_rag.log`, `crew_router.log`, `crew_retriever.log`, `run_summary.csv`, `routing_check.csv`, `swimlanes.png` and `summary_charts.png`.

## Files

```
agentic-rag-router-retriever/
├── README.md
├── Agentic_RAG_Router_Retriever.ipynb
├── requirements.txt
├── transformer_research_paper-dataset.pdf   # add the course dataset here
└── logs/                                    # created when the notebook runs
```
