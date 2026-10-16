# Feature Prioritization Agent

An orchestrator agent ranks product features by consulting three stakeholder agents: a **User Advocate**, a **Tech Lead** and a **Business Analyst**. The design rule is **the LLMs reason, code decides**. The agents judge evidence, while the ranking, sensitivity analysis and human-review flags are computed in Python and stay reproducible.

**Notebook:** [`feature_prioritization_agent.ipynb`](feature_prioritization_agent.ipynb). It runs on an OpenAI or Anthropic API key; the offline tests need no key.

## How it works

```
Task ─▶ Orchestrator agent (hand-written tool-calling loop)
          │
          ├─ get_stakeholder_assessment × 9  ── runs in parallel
          │     └─ persona agent → JSON → Pydantic validation
          │          (score 1–10, rationale, cited signal IDs;
          │           invalid or uncited output is retried with the error)
          │
          ├─ rank_features  ── pure Python
          │     ├─ weighted scores
          │     ├─ sensitivity across 4 weightings
          │     └─ disagreement ≥ 5 points → flagged for human review
          │
          └─ written recommendation ──▶ checked against the computed ranking
```

| Component | What it does |
|---|---|
| Stakeholder agents | Each persona reads the feature brief and nine customer signals (tickets, interviews, engineering estimates, sales and churn data), then returns a validated `Assessment`. A score citing a signal ID that doesn't exist fails validation. |
| `call_structured` | Validates model output against a Pydantic schema; on failure it sends the exact validation error back and asks for corrected JSON, up to a retry limit. |
| `rank_features` | Computes the ranking in code, refuses to rank until all nine assessments exist, and tests whether the top choice holds under user-first, feasibility-first and business-first weightings. |
| Human-review flags | A feature whose stakeholder scores differ by 5 or more points (for example, high user demand but low feasibility) is flagged for a person instead of being averaged away. |
| Agent loop | Model → tool calls → results → repeat, without a framework. Unknown tools and bad arguments become error messages the model can recover from; independent tool calls run in parallel; every call is traced; `max_steps` stops runaway loops. |
| Consistency check | Verifies that the agent's written recommendation names the code-computed top feature and every flagged feature. |

## Offline tests

Scripted models stand in for the LLM, so the control logic is tested without API calls:

1. Scoring, sensitivity and disagreement flags match hand-computed values.
2. An out-of-range score and an invented signal ID are each retried with the validation error; persistent failure raises.
3. A full agent run completes nine parallel assessments, recovers from a hallucinated tool name, and produces a recommendation that passes the consistency check.
4. Ranking is blocked until all assessments exist.
5. The step limit stops a model that never finishes.

## Run it

1. Open the notebook in Google Colab.
2. Add `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` under **Secrets** (🔑) with notebook access on, and set `PROVIDER` in Step 5.
3. Run all cells. Without a key, run Steps 1–4, 6 and 7 for the offline tests.

The product, signals and estimates are a fictional scenario for demonstration.

## What I'd add next

- Real ticket and interview data as the evidence source, retrieved with RAG instead of a fixed list.
- A stored decision log (inputs, scores, flags, approver) for auditing.
- A LangGraph version that pauses for human approval on flagged features before the recommendation is finalised.

*Built from a course demo (fixed-score lookup tools with the LLM summing scores) and extended with the stakeholder agents, schema validation, code-based scoring, human-review flags, error handling, parallel execution and offline tests.*
