# AutoGen Agent Chain for Automated Code Testing, Review and Debugging

An agent chain built with [AutoGen AgentChat](https://microsoft.github.io/autogen/) that does code QA automatically. One agent writes a function, a second writes `pytest` tests for it, and the tests run in a separate process with coverage measured. When tests fail, a **Reviewer** agent decides whether each failing test is wrong or the code is, wrong tests are set aside, and a **Debugger** agent fixes the code. Once everything passes, the Tester gets the **coverage report** and adds tests for code that was never run.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/<your-username>/<your-repo>/blob/main/AutoGen_Code_Testing_Debugging_Chain.ipynb)

## How it works

```
CodeGen ──► solution.py ──────┐
Tester  ──► test_solution.py ─┴─► pytest + coverage
                                    │
             ┌──── tests fail ──────┤
             ▼                      │ all pass
        Reviewer: wrong test        ▼
        or wrong code?         coverage below target?
          │          │            │ yes          │ no
   set aside the     │            ▼              ▼
   wrong tests       ▼        Tester adds    ✅ done, save
          └──► Debugger fixes   tests for       artifacts
               solution.py      missed lines
                    └────── run again ◄──────────┘
```

| Agent / step | Role |
|---|---|
| **CodeGen** | Writes `solution.py` from the specification |
| **Tester** | Writes `pytest` tests from the specification. Later, it gets the code with line numbers and the exact lines and branches that were never run, and adds tests for them |
| **Test Runner** | Plain Python, not an agent. Runs `pytest` with `pytest-cov` in an isolated subprocess, and reports pass/fail counts, the failing test names, and statement + branch coverage |
| **Reviewer** | When tests fail, works out the correct answer for each failing test from the specification, then judges it `WRONG_TEST` (the test contradicts the specification) or `CODE_BUG` (the code is wrong) |
| **Debugger** | Gets the pytest output, the tests and the current code, and returns a fixed `solution.py` |

## The task: a date parser

The chain builds `parse_date(text: str) -> datetime.date`, a function with plenty of edge cases:

- **Four formats:** `2026-11-05`, `11/05/2026` (month first), `November 5, 2026` and `5 Nov 2026`
- Full or 3-letter month names, in any letter case, with surrounding whitespace ignored
- Leap years: `2024-02-29` is valid, `2025-02-29` raises `ValueError`
- Dates that don't exist (`2026-02-30`), empty strings and unsupported formats raise `ValueError`, and input that isn't a string raises `TypeError`

The whole specification lives in one `TASK` dictionary, and all four agents' instructions are built from it, so changing `TASK` points the chain at a different function.

## Design choices

### The Reviewer, and its guardrails

A test written by a language model can be wrong. Without a Reviewer, the Debugger would "fix" correct code to match a bad test. Before each Debugger round, the Reviewer judges every failing test. How it's asked matters:

- **Work out the answer first.** For each failing test, the Reviewer must write down what the specification says the correct result is (`spec_says`) and what the test asserts (`test_expects`) before giving a verdict. If they differ, the test is wrong.
- **One test at a time.** It sees each failing test's own source code and its own pytest error, not one long log where a single wrong test gets lost among many real failures.
- **No access to the code.** The Reviewer never sees `solution.py`, so it can't be swayed by what the code happens to do.
- **A fresh start every time.** Its conversation is reset before each review, so it isn't anchored to earlier verdicts.
- **An optional stronger model.** `REVIEWER_MODEL` can point the Reviewer at a stronger model (for example `gpt-4o`) while the other agents stay on `gpt-4o-mini`.

The orchestrator then applies guardrails before removing anything:

- **Only failing tests can be set aside.** A verdict about a test that passed is ignored.
- **A cap for the whole run.** At most 30% of the original tests (`MAX_QUARANTINE_FRACTION`) can be set aside. A verdict that would go over the limit is rejected entirely, since "most of the tests are wrong" more likely means the code is wrong.
- **When the spec is silent, blame the code.** The Reviewer chooses `CODE_BUG` only if the requirements genuinely don't determine the result.
- **Nothing is lost.** Set-aside tests are cut out of the test file, with everything else in the file kept, comments included. They're saved to `quarantined_tests.py` along with the Reviewer's reasons, so a person can check them.

After tests are set aside, the tests run again before any code changes. The Debugger only acts on the failures that are left.

### pytest and coverage feedback

- **pytest instead of a homemade runner.** pytest reports each failing test by name, with a short traceback. If the test file defines no tests, pytest reports "no tests ran", which counts as a failure, so an empty test file can't "pass".
- **Coverage-driven tests.** When all tests pass but statement + branch coverage is below `COVERAGE_TARGET` (95%), the Tester gets `solution.py` with line numbers plus the exact missed lines and branches, and writes new tests for them (up to 2 rounds). If the new tests fail, they go through the Reviewer and Debugger like any other test.
- **No silent overwrites.** If an added test reuses an existing name, it's renamed (`test_iso` → `test_iso_2`), so it can't quietly replace the original.

### Showing every path

The notebook does two runs. The first is a normal run from scratch. The second starts from **two deliberate problems**: code that only understands ISO dates, and an injected test claiming `03/02/2026` means 3 February. The specification says the month comes first, so it's actually 2 March. A good second run shows the Reviewer setting aside exactly that test, then the Debugger fixing the code to pass the rest.

### Also

- **Isolated execution.** Generated code runs in a separate Python process with a 30-second timeout, so a crash or an infinite loop can't take down the notebook.
- **A full audit trail.** Each run gets a timestamped folder under `runs/` containing the final `solution.py`, `test_solution.py`, any `quarantined_tests.py`, and a `log.jsonl` record of every agent reply, verdict, test run, fix and coverage round.
- **Consistent results.** `temperature=0` keeps the generated code, tests and verdicts consistent from run to run.

## Example output

### What a real run taught me

The first version of the Reviewer, run with `gpt-4o-mini` on 2026-11-05, **missed the injected wrong test**:

```
Run                Passed  Tests (first -> final)  Coverage (first -> final)  Debug  Cov rounds  Set aside
--------------------------------------------------------------------------------------------------------------
generate           True    7/9 -> 9/9              100.0% -> 100.0%           1      0           -
review_debug_demo  False   5/10 -> 9/10            100.0% -> 95.7%            3      0           -
```

The Debugger produced a correct parser, reading `03/02/2026` month first as the spec requires, but the wrong test stayed in. The Debugger then spent all 3 rounds trying to satisfy a test that contradicts the spec. That version of the Reviewer saw one long pytest log in which the wrong test was a single failure among many, kept its conversation history between rounds, and was told to blame the code when unsure.

The current version fixes that: it judges each test separately, works out the correct answer before giving a verdict, starts fresh each review, and never sees the code. The summary also gained a **Still failing** column.

### After the fix

Same model (`gpt-4o-mini`), same date, same deliberately broken starting point:

```
Run                Passed  Tests (first -> final)  Coverage (first -> final)  Debug  Cov rounds  Set aside                 Still failing
---------------------------------------------------------------------------------------------------------------------------------------
generate           True    7/9 -> 9/9              100.0% -> 100.0%           1      0           -                         -
review_debug_demo  True    5/10 -> 9/9             100.0% -> 100.0%           2      0           test_slash_date_example   -
```

The Reviewer set aside exactly the injected wrong test, with a correct reason. This is saved in `quarantined_tests.py`:

```python
# test_slash_date_example: The input '03/02/2026' is in MM/DD/YYYY format, which correctly translates to March 2, 2026.
def test_slash_date_example():
    assert parse_date("03/02/2026") == date(2026, 2, 3)
```

The Debugger then turned the ISO-only starting code into a full parser in 2 rounds. It passes all 9 remaining tests with 100% statement and branch coverage. Better prompting fixed the problem, with no need for a bigger model.

## Run it

1. Open the notebook in Google Colab (use the badge above, or upload `AutoGen_Code_Testing_Debugging_Chain.ipynb`).
   - During install, pip may warn about `protobuf` conflicts with preinstalled Colab packages like TensorFlow. The notebook doesn't use those packages, so the warning is safe to ignore.
2. Click the 🔑 **Secrets** icon in the left sidebar, add `OPENAI_API_KEY` with your OpenAI key, and turn on **Notebook access**.
3. Choose **Runtime → Run all**.

The notebook uses `gpt-4o-mini`, and a full run (both chains) typically costs around a cent. These settings in Steps 3 and 4 control the loop:

| Setting | Default | Meaning |
|---|---|---|
| `MODEL` | `gpt-4o-mini` | OpenAI model used by CodeGen, Tester and Debugger |
| `REVIEWER_MODEL` | same as `MODEL` | Model for the Reviewer; try `gpt-4o` for a stronger judge |
| `MAX_DEBUG_ROUNDS` | 3 | Debugger attempts before giving up |
| `MAX_COVERAGE_ROUNDS` | 2 | Times the Tester may add tests for uncovered code |
| `COVERAGE_TARGET` | 95.0 | Statement + branch coverage (%) the tests must reach |
| `MAX_QUARANTINE_FRACTION` | 0.3 | Largest share of tests the Reviewer may set aside in one run |

### Run locally instead

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="your-key"
jupyter notebook AutoGen_Code_Testing_Debugging_Chain.ipynb
```

If no key is found, the notebook asks for it in a hidden input box.

## Known limitations

- **The Reviewer can be wrong too.** It's a language model, and an earlier version missed a wrong test (see "What a real run taught me"). Better prompting fixed that case, but it isn't a guarantee. The guardrails limit the damage, but it can still set aside a correct test or miss a wrong one. That's why set-aside tests are saved for a person to review, and why the summary lists any tests still failing.
- **Wrong tests are set aside, not fixed.** The Reviewer removes a wrong test but doesn't write a corrected one, so the behaviour that test was meant to check may go untested.
- **Coverage isn't correctness.** 100% coverage means every line and branch ran, not that the tests would catch every bug. Mutation testing would measure that.
- **Only the solution gets fixed.** If the test file has a syntax error, the chain can't repair it.
- **It runs code a model wrote.** The subprocess and timeout guard against crashes and hangs, but they aren't a security sandbox. Colab is a disposable environment; take more care before running this on your own machine.

## Possible extensions

- Let the Tester rewrite a test the Reviewer flags as wrong, instead of only setting it aside
- Add mutation testing (for example with `mutmut`) to check that the tests catch real bugs
- Run several tasks from a list and report a pass rate per model
- Compare models (for example `gpt-4o-mini` vs `gpt-4o`) on rounds needed and final coverage

## Tech stack

Python · AutoGen AgentChat (`autogen-agentchat`, `autogen-ext[openai]`) · OpenAI API · pytest · pytest-cov · Google Colab

## Credits

Based on *Lesson 02, Demo 01: Implementing an AutoGen Agent Chain for Automated Code Testing and Debugging* from my Agentic AI coursework. I adapted it for Google Colab and GitHub and extended it:

- Replaced the palindrome example with a date parser that has four formats, leap years and invalid dates
- Added a **Reviewer** agent that separates wrong tests from real bugs. It works out the correct answer first, judges each test separately and never sees the code, with guardrails (failing tests only, a cap for the whole run, saved reasons)
- Switched to **pytest + pytest-cov**, and added a coverage feedback loop where the Tester writes tests for missed lines and branches
- Added a second run with deliberately buggy code and a deliberately wrong test, which shows the Reviewer and Debugger working
- Switched from Azure OpenAI to the OpenAI API, with the key kept in Colab Secrets
- Defined the task once in `TASK`, gave each run its own `runs/` folder, reset the agents between runs, and added `temperature=0`
