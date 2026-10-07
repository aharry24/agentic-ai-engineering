# 03 · Generative AI Tech Stack & Prompt Engineering

This module covers the **orchestration layer** of the agentic AI stack: how frameworks turn individual LLM calls into multi-step, multi-agent workflows. It also covers how **agentic RAG** decides *where* to look for an answer.

There are two parts:

1. **One workflow, three frameworks.** The same Analyst → Strategist pipeline built in **LangGraph**, **CrewAI** and **Microsoft Agent Framework**. Each is extended past the basic version to show what that framework does best: a guardrail loop, a manager agent, and agent-to-agent handoffs.
2. **Agentic RAG with Claude.** A router–retriever system that sends each question to a research paper, live web search, or the model's own knowledge.

All notebooks run on **Anthropic Claude (Sonnet 4.5)** and are saved with their outputs.

---

## Contents

| Demo | Framework | What I built on top of the base demo | Notebook |
|---|---|---|---|
| Analyst → Strategist + **guardrail loop** | LangGraph | A fact-checking node that loops back to the Strategist if it cites a signal that doesn't exist | [`langgraph_analyst_strategist.ipynb`](demos/analyst-strategist-multi-framework/langgraph_analyst_strategist.ipynb) |
| Analyst → Strategist: **sequential vs. hierarchical** | CrewAI | A manager agent that delegates work, plus a cost comparison of the two processes | [`crewai_analyst_strategist.ipynb`](demos/analyst-strategist-multi-framework/crewai_analyst_strategist.ipynb) |
| Analyst → Strategist: **sequential vs. handoff** | Microsoft Agent Framework | Handoffs where the Strategist can send the conversation back to the Analyst | [`agent_framework_analyst_strategist.ipynb`](demos/analyst-strategist-multi-framework/agent_framework_analyst_strategist.ipynb) |
| **Agentic RAG** router–retriever | CrewAI + Docling + Chroma | A transparent PDF pipeline, local embeddings, and a router that knows what the document contains | [`agentic-rag-anthropic/`](demos/agentic-rag-anthropic) |

---

## Part 1: One workflow, three frameworks

### The scenario

An assistant reads customer signals and recommends one feature to build next, without making anything up:

```
- User interview (Maria, SMB owner): "I got lost during setup and gave up before finishing."
- Support ticket #4821: "Can't find where to invite my team members. Confusing menu."
- Competitor teardown (RivalApp): just shipped a guided setup checklist with a progress bar.
- Support ticket #4903: "Wish there was a quick tour when I first logged in."
```

- **Analyst:** extracts 2–3 themes and cites the signal behind each one.
- **Strategist:** recommends ONE feature, using only the Analyst's themes.

Keeping the task identical makes the frameworks directly comparable. The only thing that changes is *how the flow is controlled*.

### How the three frameworks compare

| | LangGraph | CrewAI | Microsoft Agent Framework |
|---|---|---|---|
| Mental model | Explicit state graph | Role-based crew | Agents plus pre-built workflow patterns |
| You define | Nodes, edges, shared state | Agents (role, goal, backstory) and Tasks | Agents and a Builder (Sequential, Handoff, GroupChat…) |
| Who decides what runs next | **You**: edges and conditional edges | **The Process**: sequential order, or a manager agent | **The agents**: each one calls handoff tools |
| How a loop back works | `add_conditional_edges` (one call) | No built-in way; needs a custom Flow or manual retry | `add_handoff(strategist, [analyst])` |
| Control vs. code | Most control, most code | Least code, least control | Both: low-level `WorkflowBuilder` or ready-made patterns |
| Maturity | Years in production | Years in production | Young (GA April 2026) |

### 1. LangGraph: a guardrail with a loop back

```
START → analyst → strategist → guardrail ──pass──→ END
                      ▲             │
                      └───retry─────┘  (up to MAX_ATTEMPTS = 3)
```

The Strategist is *told* not to invent signals. The guardrail *checks* it, in two layers:

1. **A regex check** (free, instant): every ticket number cited must exist in the input signals.
2. **An LLM judge**: catches invented sources a regex can't see, such as "our NPS survey". It only runs if layer 1 passes, so an obvious failure doesn't cost an extra API call.

If the guardrail fails, the graph loops back with feedback. If it's still failing after three attempts, the run ends and is marked `guardrail_passed = False` for human review.

**Results:**
- **Live run:** the guardrail passed on the first attempt, with a recommendation for a guided onboarding checklist with progress tracking.
- **Offline loop test:** a scripted fake model forces hallucinations, so the loop can be shown without spending API credits:

| Attempt | What the Strategist cited | Caught by | Result |
|---|---|---|---|
| 1 | Ticket **#5120** (doesn't exist) | Regex | Loop back |
| 2 | "Our Q3 NPS survey" (doesn't exist) | LLM judge | Loop back |
| 3 | Only real signals | — | ✅ Accepted |

### 2. CrewAI: sequential vs. hierarchical

| | Version A: Sequential | Version B: Hierarchical |
|---|---|---|
| Who decides the order | You: tasks run top to bottom | A **Product Team Lead** manager agent |
| Tasks | Two step-by-step tasks, each with an assigned agent | One goal-level task with no agent assigned |
| Quality control | None | The manager reviews each answer and rejects ungrounded work |

To log what the manager did, I hooked into CrewAI's **event bus**. An earlier version used a `step_callback`, but CrewAI only attaches that to worker agents, never to the manager, so it recorded nothing.

**Results from the saved run:**

| | Sequential | Hierarchical |
|---|---|---|
| Call order chosen by | you | manager (Analyst → Strategist) |
| Manager delegations | — | 2 |
| LLM requests | 12 | 19 |
| Total tokens | **6,208** | **15,260** (≈2.5×) |

Both versions recommended a guided setup checklist with a progress indicator. The manager worked out on its own that the analysis had to come first. For a fixed two-step task, though, hierarchical mode costs about 2.5 times as many tokens for the same answer. A manager pays off when the path really does depend on the content.

### 3. Microsoft Agent Framework: sequential vs. handoff

| | Version A: `SequentialBuilder` | Version B: `HandoffBuilder` |
|---|---|---|
| Flow | Fixed: Analyst → Strategist, once | Agents decide at runtime who speaks next |
| Can the Strategist ask for more? | No | Yes, by calling a `handoff_to_Analyst` tool |
| When it ends | After the last agent | When a custom `termination_condition` returns true (the Strategist posts `FINAL RECOMMENDATION:`), with an 8-turn cap |

**Results:** the handoff trail was **Analyst → Strategist → Analyst → Strategist**, so the Strategist handed back to the Analyst once, and the run ended with a grounded recommendation for guided onboarding with a progress-tracked checklist.

**What the trace showed:** the Analyst handed off *before* writing any themes, so the Strategist sent it back for missing analysis rather than for "more depth". The routing worked as designed. Stricter instructions for the Analyst ("write your theme *then* hand off") would make the first pass more reliable. When agents control the flow, you have to check the trace, not just the final answer.

### Takeaways

- **All three frameworks reached the same recommendation**: a guided onboarding checklist with progress tracking. Here the choice of framework changed *control, cost and traceability*, not the answer.
- **Pick the control model that matches the problem:** explicit graphs when you need guaranteed checks and loops (LangGraph), role-based crews for fast, readable pipelines (CrewAI), and agent-driven handoffs when the path depends on what the agents find (MAF).
- **Flexibility has a cost:** the hierarchical crew used about 2.5 times the tokens of the sequential one for the same output.
- **Guardrails belong in code, not only in prompts.** "Do not invent signals" is a request; the guardrail node *enforces* it.

---

## Part 2: Agentic RAG with Claude

A **Router Agent** labels each question `pdf_search`, `web_search` or `generate`. A **Retriever Agent** then uses the matching tool and cites its source. The PDF pipeline is built step by step rather than hidden inside one tool: **Docling** parsing → chunking → local **MiniLM** embeddings → **ChromaDB** → a custom CrewAI tool.

**Results:** **4 out of 4** questions routed correctly. The PDF route returned the paper's **28.4 BLEU** score for English-to-German translation word for word.

**Key fix:** at first, the Router answered a question about multi-head attention from memory (`generate`), because it didn't know what the PDF contained. Giving it the document's section headings, plus a rule to prefer the PDF whenever the PDF covers the topic, fixed the routing.

Full write-up: [`demos/agentic-rag-anthropic/README.md`](demos/agentic-rag-anthropic/README.md)

---

## Running the notebooks

All notebooks are written for **Google Colab**:

1. Add `ANTHROPIC_API_KEY` under **Secrets** (🔑) and turn on notebook access. The RAG demo also needs `TAVILY_API_KEY` for the web route. The LangGraph and CrewAI notebooks also ask for an optional `ANTHROPIC_WORKSPACE_ID`, for API keys that are scoped to a workspace.
2. Run the install cell, then **Runtime ▸ Restart session**, then run the remaining cells.

The **Microsoft Agent Framework** notebook pins exact package versions, because MAF's provider packages are still in beta and change quickly. The other notebooks install the latest versions. If a library update breaks a run, see the version notes in each notebook.

## Skills demonstrated

LangGraph (state graphs, conditional edges, cycles) · CrewAI (sequential and hierarchical processes, manager agents, the event bus) · Microsoft Agent Framework (`SequentialBuilder`, `HandoffBuilder`, autonomous mode, termination conditions) · LLM-as-judge guardrails · offline testing with fake LLMs · agentic RAG and query routing · Docling · ChromaDB · Hugging Face embeddings · Anthropic Claude
