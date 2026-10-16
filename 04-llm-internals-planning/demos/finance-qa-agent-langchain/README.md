# Finance Q&A Agent

An agent that answers business and finance questions for product managers, such as growth, churn, unit economics and break-even. The design rule is **the LLM plans, code calculates**. The model lists the numbers it will use and writes the calculation. Code checks that every number came from the question, runs the calculation in a sandbox, and sends any error back to the model to fix.

| Notebook | What it does |
|---|---|
| [`finance_qa_agent.ipynb`](finance_qa_agent.ipynb) | The agent, offline tests, and an 18-question evaluation against a direct-answer baseline |
| [`finance_qa_agent_stress_test.ipynb`](finance_qa_agent_stress_test.ipynb) | 16 harder questions, two model sizes, and the fixes found by stress-testing |

Both run on an OpenAI or Anthropic API key. The offline tests need no key.

## Results

### Stress test: 16 hard questions

Every question has distracting numbers, a unit conversion, or 4–5 chained steps. Each is answered by the same model two ways: **directly** (one LLM call, no tools) and through the **agent**. Both use minimal reasoning effort.

| | gpt-5-nano direct | gpt-5-nano agent | gpt-5-mini direct | gpt-5-mini agent |
|---|---|---|---|---|
| **Correct** | 1 | **8** | 3 | **15** |
| **Wrong number returned** | 9 | 1 | 12 | **0** |
| Asked to clarify | 6 | 7 | 1 | 0 |
| Rejected by the checks | 0 | 0 | 0 | 1 |

- **Accuracy:** with the same model, the agent took gpt-5-mini from **3/16 to 15/16**. The direct errors were real reasoning mistakes, such as using a distractor number or dropping a step, not formatting problems.
- **Safety:** across both models, answering directly returned **21 wrong numbers**; the agent returned **1**. When the agent can't produce a verified answer, it asks or declines instead of guessing.

### Main evaluation: 18 standard questions

| | Direct | Agent |
|---|---|---|
| Numeric answers | 13/13 | 13/13 |
| Ambiguous: asked, or stated its assumption | 0/2 | **2/2** |
| Missing data: asked instead of guessing | 3/3 | 3/3 |
| **Overall** | 16/18 | **18/18** |

On easy questions the model's arithmetic was fine on its own, so accuracy tied. The agent won on ambiguity: it stated the interpretation it chose, where the direct answer gave a number with no caveat. One agent reply was rejected by a check and corrected on retry.

## How it works

```
Question
   │
   ▼
LLM → JSON reply ── "clarify" + question  ──────────────▶ ask the user
   │                 or "answer" + inputs, assumptions, code
   ▼
check_inputs ── each input's source phrase must be in the question,
   │            and its value must match that phrase ("8%" → 0.08 or 8, not 0.8)
   ▼
to_fractions ── percentages always reach the code as fractions (72% → 0.72)
   ▼
validate_code ── AST allow-list: no imports, attributes or unknown calls;
   │             no hard-coded numbers except 0, 1, 2, 12, 100
   ▼
run_sandboxed ── inputs injected as variables; printed result captured
   │
   └─ any failure → the exact error is sent back to the model (up to 3 attempts)
```

| Component | What it does |
|---|---|
| **Structured reply** | A Pydantic schema: either a clarifying question, or inputs (name, value, source phrase), assumptions, code and an explanation. |
| **Input provenance** | Every number must be traced to a phrase in the question. A misread value (0.8 for 8%) or an invented source is rejected. |
| **No hard-coded numbers** | The code may only use the verified inputs by name. Without this rule, the model could write `10000 * 1.08` and bypass the input check. |
| **Sandbox** | Generated code runs with a few safe built-ins and nothing else. |
| **Retry with feedback** | A rejected reply goes back to the model with the reason, so it can correct itself. |
| **Ask instead of guess** | Missing data leads to a clarifying question; an ambiguous question is answered with the assumption stated. |

## What the stress test found, and the fixes

The first stress-test run exposed four problems, all now fixed in the stress-test notebook:

| Problem | Fix | Effect |
|---|---|---|
| **A unit bug the checks couldn't see.** gpt-5-nano used gross margin as 0.72 but churn as 3.5, and returned 0.03 instead of 3.25. Every input really was in the question, so the provenance check passed. | `to_fractions` converts every percentage input to a fraction, whichever way the model wrote it, and code that divides a percentage by 100 again is rejected with the reason. | An offline test replays the exact bug: it's caught, and the corrected reply returns 3.25. |
| **The small model hard-coded numbers** in its code, so 6 replies were rejected. | One worked example in the prompt. A test confirms the example passes the agent's own checks. | Rejections fell from 6 to 0; nano's agent accuracy rose from **2/16 to 8/16**. |
| **The small model asked "shall I proceed?"** on clear questions. | A tighter rule: ask only when a number is missing or two readings give different answers. | No change: nano still asked 7 times. Small models don't reliably follow "never do X" rules. |
| **A refusal and a wrong number both scored ✗.** | The scorecard counts wrong numbers separately. | The safety result above became measurable. |

The direct prompt gets the same rule and the same example question, so the comparison stays fair.

The key lesson: **input checks prove where a number came from, not that it was used correctly.** Units are now enforced in code, but a wrong formula is still possible, which is why the evaluation measures accuracy and not just whether the checks passed.

## Offline tests

Scripted models stand in for the LLM:

1. Valid readings of inputs are accepted; misread values and invented sources are rejected.
2. The sandbox runs injected inputs and blocks hard-coded numbers, unknown names, imports and attribute tricks.
3. A misread input is sent back with the reason and corrected on the next attempt.
4. The agent clarifies when it should, and gives up cleanly after repeated invalid replies.
5. Scoring handles answers, clarifications and stated assumptions.
6. *(Stress-test notebook)* Percentage conversion, the replayed Q9 unit bug, the worked example, and the outcome labels.

## Run it

1. Open a notebook in Google Colab.
2. Add `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` under **Secrets** (🔑) with notebook access on.
3. Set `PROVIDER` (main notebook: Step 5; stress test: Step 5, where you can also check the model names).
4. Run all cells. Without a key, the offline tests in Step 4 still run.

**Stack:** LangChain · Pydantic · Python `ast` for code validation · OpenAI or Anthropic. No Azure needed.

## Limitations and next steps

- **A false rejection in the latest run.** gpt-5-mini declared `months_in_year = 12` as an input, but "12" isn't in the question, so it was rejected three times. 12 is an allowed constant in the code. Next fix: say so explicitly in the prompt, and return a specific error ("12 is a standard constant; use it directly in the code").
- **Port the fixes to the main notebook.** Percentage conversion and the worked example currently live only in the stress-test notebook.
- **Small models over-clarify.** A deterministic check on clarifying questions, or a reply format that makes asking for permission impossible, may work better than a prompt rule.
- **Run-to-run variance.** Results are from single runs; repeat runs would give a range.
- **Sandbox.** The AST allow-list is a demo-level safeguard. Production code execution belongs in an isolated container.

*Built from a course demo (a LangChain agent with a Python REPL tool on Azure OpenAI) and extended with structured replies, input provenance checks, a validated sandbox, retry with feedback, clarification handling, a baseline comparison and a stress test.*
