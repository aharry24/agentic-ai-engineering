# Validated Research Agent with LangGraph

A fintech research assistant that answers questions about fraud detection in UPI (India's Unified Payments Interface) payments using live web search, **checks its own answers before delivering them**, remembers the conversation, and is evaluated on whether it searches when it should.

```
                ┌──────────────────────── fail, attempts left: retry with feedback ─┐
                ▼                                                                   │
 question ─▶ research ─────────────▶ validate ─────── pass ──────▶ finalize ─▶ answer
            (ReAct agent:              (citation checks              ▲
             search or answer)          + LLM judge)                 │
                                            └──── fail, no attempts left ┘ (answer marked unverified)

 checkpointer: every turn is saved under a thread_id, so follow-up questions see the conversation
```

## What's inside

| Part | What it shows |
|---|---|
| **ReAct agent** | A tool-using agent (`create_agent` + Tavily) that decides for itself whether a question needs a web search |
| **Validated research graph** | A custom `StateGraph`: researcher → validator → conditional edge that retries with feedback, up to 3 attempts, then marks the answer unverified rather than presenting it as trustworthy |
| **Conversation memory** | A checkpointer keyed by `thread_id`: follow-ups like "which of those are RBI-mandated?" work on the same thread and fail, as they should, on a new one |
| **Tool-decision eval** | 16 labelled questions measuring missed vs. unnecessary searches, compared across Claude and OpenAI |

## Validation in two layers
1. **Deterministic checks** in plain Python: every cited URL must have actually been retrieved during the run, and an answer built on search results must cite them.
2. **LLM judge** with structured output (`passed`, `issues`): is every factual claim supported by the source excerpts, and are sources recent enough for the question?

The judge's specific issues become the researcher's feedback on the next attempt.

## Eval results

<!-- After your first run, paste the summary table from Part 4 here. -->

| Provider | Accuracy | Missed searches | Unnecessary searches | Avg seconds |
|---|---|---|---|---|
| Claude | 100% | 0 | 0 | 8.3 |
| OpenAI | 100% | 0 | 0 | 18.5 |

A *missed search* means the agent answered a current-events question from training data, which is the dangerous error. An *unnecessary search* only costs time.

## Run it

**Google Colab:** open `validated_research_agent.ipynb`, add `TAVILY_API_KEY` plus `ANTHROPIC_API_KEY` and/or `OPENAI_API_KEY` under Secrets (key icon in the left sidebar), set `PROVIDER`, and run all cells. With both model keys, Part 4 compares the two providers.

**Locally:**

```bash
pip install -r requirements.txt
export TAVILY_API_KEY=...
export ANTHROPIC_API_KEY=...   # and/or OPENAI_API_KEY
jupyter notebook validated_research_agent.ipynb
```

## Limitations
- The judge uses the same provider as the researcher by default; a different model as judge would be a stronger check.
- The judge sees search excerpts, not full pages.
- The eval set is small (16 questions), so differences of one or two answers are noise.
- `InMemorySaver` keeps memory only while the notebook runs; swap in a SQLite or Postgres checkpointer for persistence.

## Stack
LangGraph · LangChain · Claude / OpenAI · Tavily Search API · Pydantic · pandas
