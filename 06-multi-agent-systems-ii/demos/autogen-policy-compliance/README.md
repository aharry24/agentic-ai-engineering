# Policy Compliance Review with AutoGen (AG2 Classic)

A multi-agent system that reviews company policy documents for compliance issues, decides who must act on each document, and **measures its own accuracy** against an answer key of planted issues.

The design rule: **code decides what can be checked as a fact; agents handle what needs reading and judgement.**

**Notebook:** [`autogen_policy_compliance.ipynb`](autogen_policy_compliance.ipynb). It runs in Google Colab with an OpenAI key (Azure OpenAI is also supported). The offline tests need no key.

## How it works

```
For each document:

  Starter ──▶ Analyst ──tool call──▶ ToolExecutor ──▶ Analyst ──▶ Reviewer ──▶ TERMINATE
                 │  get_document(doc_id)        (full text)          │
                 │  get_rule_findings(doc_id)   (rule results)       │ removes duplicates,
                 ▼                                                   │ weak or unsupported findings
           draft JSON findings, each with an exact quote             ▼
                                                              final JSON findings
                                                                     │
  Code ─────────────────────────────────────────────────────────────┤
    • verify every quote against the document (reject if absent)    │
    • add the rule-engine findings                                   │
    • severity per issue type, routing by the most severe issue     ▼
                                                     report: findings.csv · routing.csv · report.json
```

| Part | Done by | Why |
|---|---|---|
| Required sections, signatures, document age | **Code** (`check_rules`, from a rules table per document type) | Yes/no facts: code is consistent and never misses one |
| Outdated references, weak controls, contradictions | **Analyst agent**, reading the full document through tools | Needs reading and reasoning |
| Quality control | **Reviewer agent** (maker–checker), then **code** checks every quoted piece of evidence | A finding that can't be quoted from the document is never reported |
| Severity and routing | **Code** (`SEVERITY`, `ROUTES`) | Who must act shouldn't depend on an LLM's mood |

**AutoGen features used:** `AssistantAgent` and `UserProxyAgent`; tool calling with `register_function` (a caller agent and an executor agent); a `GroupChat` with a **custom speaker-selection function**, so every review follows the same path and ends when the Reviewer finishes.

## Routing

| Most severe issue | Routing |
|---|---|
| Critical (weak security control) | Escalate to Legal & Executive review |
| Major (missing section or signature, contradiction) | Route to department head for approval |
| Minor (stale document, outdated reference) | Send revision request to document owner |
| None | No action: compliant |

## Evaluation

Five synthetic policies contain **11 planted issues**: 5 rule issues (missing sections, a missing signature, stale documents) and 6 judgement issues (outdated references, weak controls, contradictions). One document is deliberately **compliant**, to catch false positives.

The scorecard compares three approaches on the same documents:

| Approach | What it is |
|---|---|
| Rules only | The code rule engine alone |
| Single LLM call | One prompt with all documents and the rules, no agents and no rule engine |
| Agents + rules | This system |

It reports recall on rule issues and on judgement issues, findings outside the answer key, findings on the compliant document, and quotes that aren't in the document.

**Results:** see Step 10 of the notebook. *(Add your run's scorecard here.)*

## What changed from the course demo

The original Module 6 demo ran three agents in an automatic group chat. Its run showed several problems, each of which this version fixes:

| Problem in the original | Fix |
|---|---|
| Documents were cut to 200 characters, so the missing signature and review date were never seen | Agents read the full document through a tool |
| An agent reported the task instructions as "workflow notes in the document" | Every finding must quote the document; code rejects quotes that aren't there |
| The summary printed fixed "key findings" whatever the agents found | The report is built from the actual findings |
| One agent spoke five times in a row, four times with an empty reply; the chat ended only at the round limit | A custom speaker-selection function sets the order; the Reviewer ends the chat. No low output-token limit, which reasoning models can use up before replying |
| The compliance rules and the monitoring functions were defined but never used | The rules table drives the rule engine; the unused monitoring stub was removed |
| The coordinator agent invented notifications, IDs and deadlines | Severity and routing are decided in code; nothing is claimed that the system didn't do |
| Azure endpoint and resource name hard-coded | OpenAI by default; Azure settings come from Colab secrets |

## Run it

1. Open the notebook in Google Colab.
2. Add `OPENAI_API_KEY` under **Secrets** (🔑) with notebook access on. For Azure, set `PROVIDER = "azure"` in Step 5 and add `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_DEPLOYMENT`.
3. Run all cells. Without a key, Steps 1–4 still run the offline tests.

Outputs are written to `outputs/`: `findings.csv`, `routing.csv` and `report.json`.

**Stack:** AutoGen / AG2 Classic (`autogen` package, classic `autogen` API) · OpenAI or Azure OpenAI · pandas

**Package note:** install `autogen[openai]`, not `ag2`. Since v1.0 the `ag2` package is a separate framework with its own imports (`import ag2`) and no `autogen` module.

## Limitations

- The documents and answer key are synthetic and small, so the scores show the method rather than production accuracy.
- LLM results vary between runs; run the evaluation more than once before quoting numbers.
- Section checks look for `Name: value` lines, which suits structured policies; free-form documents would need a document parser.

*Built from a course demo (Lesson 01 Demo 02, Module 6) and rebuilt with a rule engine, tool-using agents, a maker–checker review, evidence verification, deterministic routing, an evaluation against planted issues, and offline tests.*
