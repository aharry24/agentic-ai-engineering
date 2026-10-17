# Spec Team

A MetaGPT-style multi-agent pipeline: six role-specialized Claude agents turn one business brief into a complete product specification, then review and revise their own work.

```
                    +--> Designer --+
 Brief --> PM (PRD) |               +--> Project Lead (plan) --> QA review --> PM closes the loop
                    +--> Engineer --+
```

Built directly on the Anthropic Python SDK, with no agent framework. Each agent is a role, an SOP (system prompt) and a role-specific task. Agents share no memory; each sees only the documents handed to it. The Designer and Engineer run in parallel on the same PRD.

## What I learned building it

The first version *looked* like it worked. It ran end to end and produced a 30,000-character spec. On review, it had three silent failures:

| Failure | Cause | Fix |
|---|---|---|
| Every document was cut off mid-sentence, and whole required sections (Out of Scope, API Endpoints, Top 3 Fixes) were missing | All six agents hit `max_tokens`; nothing checked `stop_reason` | Detect `stop_reason == "max_tokens"` and retry with a larger budget |
| The Designer rewrote the PRD instead of writing design considerations | Every agent received the brief *"Generate a complete product spec..."* as its task, which overrode its SOP | Each agent gets its own task; the brief is passed as labelled background |
| Neither problem was noticed | SOPs said "EXACTLY these sections" but nothing verified it | Headings are validated after every call; a miss triggers one retry with feedback |

The failures also compounded: downstream agents reviewed truncated documents, so some "gaps" the QA agent reported were really just text that had been cut off. The lesson: **in a multi-agent pipeline, validate every handoff**, because each agent trusts its inputs completely.

## Validation report

Every run prints a per-agent report: attempts, whether the document finished, missing sections, unrequested sections (a sign of role drift) and token usage.

| Agent | Received | Attempts | Complete | Missing sections | Extra sections | In tok | Out tok |
|---|---|---|---|---|---|---|---|
| Product Manager | brief | 1 | yes | - | - | 359 | 2,715 |
| Designer | brief + PRD | 1 | yes | - | - | 2,766 | 3,160 |
| Engineer | brief + PRD | 2 | yes | - | - | 5,610 | 15,597 |
| Project Lead | brief + PRD + Design + Tech design | 2 | yes | - | - | 21,326 | 8,589 |
| QA Reviewer | brief + PRD + Design + Tech design + Plan | 3 | **truncated** | Top 3 Fixes | - | 40,962 | 31,000 |
| PM (closing) | brief + PRD + QA review | 2 | yes | - | - | 11,712 | 9,557 |
| **Total** | | | | | | **82,735** | **70,618** |

**5/6 documents passed validation.**


## Experiment: what is the QA reviewer worth?

Swapping in a QA agent that approves everything showed how much work the review step does. QA's output fell from about 1,200 tokens to 38, and the closing PM's response roughly halved, because there was nothing left to decide. With real QA, the PM made concrete calls the original spec had left open: formulas for combo multipliers and streak-recovery cost, a single definition of the streak deadline, and dropping an unrequested backfilling feature that the Engineer and Project Lead had introduced on their own.

The notebook reruns this comparison automatically.

## Run it

**Google Colab:** open `spec_team.ipynb`, add `ANTHROPIC_API_KEY` under Secrets (key icon in the left sidebar), then run all cells.

**Locally:**

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
jupyter notebook spec_team.ipynb
```

Set `ANTHROPIC_MODEL` to use a different Claude model. The run writes the full spec, with its validation report, to `product_spec.md`.

## Limitations

- Section validation checks structure, not quality.
- QA is the same model reviewing its own work; a different model or deterministic cross-document checks would be stronger.
- The PM's decisions are recorded but not fed back to revise the PRD. That's the natural next iteration.

## Stack

Python · Anthropic SDK · `concurrent.futures` for parallel agents
