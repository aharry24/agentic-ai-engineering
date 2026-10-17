# Serial vs. Parallel Agent Workflows (CrewAI + Claude)

The same agents organized two ways: a **serial** researcher → writer pipeline, and a **parallel** fan-out / fan-in where two researchers work at the same time and a writer merges their results. Every search call and task completion is timestamped, so the notebook *proves* whether the parallel branches overlapped.

Open `serial_vs_parallel_crewai.ipynb` in Colab, add `ANTHROPIC_API_KEY` and `TAVILY_API_KEY` under Secrets, and run all cells.

## Serial vs. parallel: what's actually different

```
SERIAL                                        PARALLEL (fan-out / fan-in)

Researcher ──notes──▶ Writer ──▶ result       Drug-discovery researcher ─┐
                                                                         ├──▶ Writer ──▶ combined result
(step 2 can't start until step 1 is done)     Diagnostics researcher ────┘
                                              (both start at once; writer waits for both)
```

| | Serial | Parallel |
|---|---|---|
| **Use it when** | A later step needs an earlier step's output | Subtasks are independent of each other |
| **Data flow** | Each task reads the previous task's output | Branches share nothing; a final step merges them |
| **Wall-clock time** | Sum of all steps | Roughly the slowest branch, plus the merge step |
| **Token cost** | Same work, same tokens | Same work, same tokens. Parallelism saves time, not money |
| **Failure behavior** | One failed step blocks everything after it | One failed branch can be retried without redoing the other |
| **Main risk** | Errors flow downstream into later steps | Branches can quietly duplicate or contradict each other; the merge step has to reconcile them |
| **Rate limits** | One request at a time | Concurrent requests hit API rate limits sooner |
| **CrewAI setting** | Default: tasks run in list order, and each task automatically receives all previous outputs as context | `async_execution=True` on each branch, `context=[]` so branches don't wait on each other, and a final task with `context=[branch_1, branch_2]` |

### The three CrewAI details that make or break parallelism
1. **Context is inherited by default.** Unless you set `context` explicitly, a task receives every earlier task's output, which also means it **waits** for them. In the original version of this notebook that silently turned the "parallel" run back into a serial one.
2. **Only the last task's output is returned.** `crew.kickoff()` returns the final task's result. Without a merge step, the other branch's work is still computed but disappears from the result.
3. **A crew can't end on an async task.** CrewAI requires the crew to finish with at most one asynchronous task, which is another reason the fan-in step belongs at the end.

## What I found along the way
My first version set `async_execution=True` and called it parallel. The log showed otherwise: task 1 finished before task 2 started, and task 2's output opened by noting that its context was about the *other* task's topic. CrewAI passes every earlier output forward as context by default, which also makes each task wait for the ones before it. Setting `context=[]` on each branch fixed it, and a merge task recovered the output that had been dropped. The timeline and overlap check now verify concurrency on every run instead of assuming it.

## Stack
CrewAI · Anthropic Claude · Tavily Search API · Python
