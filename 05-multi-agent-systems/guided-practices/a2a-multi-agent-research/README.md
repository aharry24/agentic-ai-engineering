# Multi-Agent Research with Google's A2A Protocol

Three agents built with **three different frameworks** (LangChain, CrewAI and a plain LLM SDK) collaborate on research questions using the **Agent2Agent (A2A) protocol**. Each agent runs as its own A2A server and publishes an **Agent Card**. A **LangGraph** orchestrator discovers them by skill and coordinates them with standard A2A messages over HTTP. No agent imports another's code.

The project comes in two forms: **notebooks** that walk through the design with saved outputs, and a **Python package** (`src/`) with a command-line interface, standalone agent servers and a pytest suite.

| Notebook | Protocol layer | Highlights |
|---|---|---|
| [`a2a_multi_agent_research.ipynb`](notebooks/a2a_multi_agent_research.ipynb) | Implemented by hand with Python's standard library | Every JSON-RPC message is visible, including a printed request and response |
| [`a2a_multi_agent_research_sdk.ipynb`](notebooks/a2a_multi_agent_research_sdk.ipynb) | Google's official [`a2a-sdk`](https://github.com/a2aproject/a2a-python) (v1.2, A2A spec 1.0) | **Streaming**: the Researcher reports each web search to the orchestrator as it happens |

The agents and the orchestrator are the same in both. Only the protocol layer changes, which shows the agents don't depend on how messages travel. Both run in Google Colab with an OpenAI or Anthropic key plus a Tavily key; the offline tests need no keys. The notebooks are self-contained, so they open in Colab with one click.

## Project structure

```
a2a-multi-agent-research/
├── README.md
├── requirements.txt
├── pyproject.toml              # package metadata, CLI entry points, pytest settings
├── .env.example                # copy to .env and add your keys
├── notebooks/
│   ├── a2a_multi_agent_research.ipynb       # protocol by hand, step by step
│   └── a2a_multi_agent_research_sdk.ipynb   # official a2a-sdk, with streaming
├── src/a2a_research/
│   ├── protocol.py             # A2A server and client (standard library)
│   ├── skills.py               # the skills each Agent Card publishes
│   ├── orchestrator.py         # LangGraph graph: discover, call, route on task state
│   ├── config.py               # provider, model and keys from the environment
│   ├── agents/
│   │   ├── extractor.py        # LangChain
│   │   ├── researcher.py       # CrewAI + Tavily, with the source check
│   │   └── writer.py           # plain SDK, with the citation check
│   ├── serve.py                # run one agent as a standalone service
│   └── main.py                 # ask a question from the command line
└── tests/                      # pytest suite: no API keys needed
    ├── conftest.py             # stub agents on real A2A servers
    ├── test_protocol.py
    ├── test_orchestrator.py
    └── test_agents.py          # agent logic with the LLM and search faked
```

## Architecture

```
                        ┌──────────────────────────────────┐
  User question ──────▶ │ Orchestrator (LangGraph)         │
                        │ A2A client: discovers agents by  │
                        │ skill, routes on task state      │
                        └──┬──────────────┬─────────────┬──┘
           A2A message/send│              │             │  (HTTP + JSON-RPC 2.0, shared contextId)
                           ▼              ▼             ▼
              ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
              │ Task Extractor │ │ Researcher     │ │ Writer         │
              │ LangChain      │ │ CrewAI+Tavily  │ │ plain SDK      │
              │ Agent Card     │ │ Agent Card     │ │ Agent Card     │
              └────────────────┘ └────────────────┘ └────────────────┘
               research brief     sourced findings    cited answer
               or input-required  (URLs checked)      (citations checked)
```

| Agent | Framework | A2A skill | Output |
|---|---|---|---|
| Task Extractor | LangChain, structured output | `extract_research_brief` | A validated brief (task, search queries, audience), or an `input-required` task with a clarifying question |
| Researcher | CrewAI + Tavily | `web_research` | Findings, each tied to a source URL |
| Writer | OpenAI / Anthropic SDK, no framework | `write_cited_answer` | A concise answer citing numbered sources |
| Orchestrator | LangGraph | A2A client | Runs extract → research → write, stopping early on `input-required` or `failed` |

## How A2A is used

| A2A concept | Where it appears |
|---|---|
| **Agent Card** at `/.well-known/agent-card.json` | Each agent publishes its name, URL and skills. The orchestrator only knows agents through their cards. |
| **Discovery by skill** | The orchestrator asks the directory for "the agent with `web_research`", never for a hard-coded address. |
| **`message/send`** (JSON-RPC 2.0) | Every agent call. Messages carry a `text` part for people and a `data` part with structured JSON for the next agent. |
| **Task lifecycle** | Each request becomes a Task. The orchestrator routes on its state: `completed` continues, `input-required` returns the agent's question to the user, `failed` stops and names the failing agent. |
| **Artifacts** | A completed task's output: the brief, the findings, the answer. |
| **`contextId`** | All calls in one run share a context ID, marking them as the same piece of work. |
| **`tasks/get`** and JSON-RPC errors | Implemented and tested: parse errors, unknown methods, invalid params, unknown tasks. |

## Two implementations of the protocol layer

**By hand (notebook 1).** About 170 lines of standard-library Python serve Agent Cards, handle JSON-RPC `message/send` and `tasks/get`, manage tasks and return standard error codes. The notebook prints a real request and response.

**With the official SDK (notebook 2).** The SDK's `DefaultRequestHandler`, `InMemoryTaskStore` and Starlette routes do that work. Each agent is wrapped in an `AgentExecutor` that publishes **events** through a `TaskUpdater`: the Task, status updates and artifacts. The client consumes them as a stream with `create_client(..., ClientConfig(streaming=True))`. Two things needed care:

- **Blocking agents, async server.** LangChain, CrewAI and the LLM SDKs block, so the executor runs them in a worker thread. Progress updates from that thread are sent back to the server's event loop safely, so each web search reaches the client as a live status update.
- **A2A 1.0 types.** Messages and tasks are protobuf objects, task states are enums like `TASK_STATE_COMPLETED`, and endpoints are listed in the Agent Card's `supported_interfaces`. The notebook pins `a2a-sdk==1.2.2`, because tutorials written for 0.3 don't run on 1.x.

The protocol-side code is about the same length in both notebooks. The SDK version isn't shorter; it does more: streaming, spec-maintained types, and access to the SDK's push notifications, gRPC and REST transports.

## Design decisions

- **Each agent checks its own output before it crosses the wire.** The Researcher drops any finding whose URL its search tool never returned, and fails the task if none survive. The Writer rejects citations that don't match a source and gets one retry with the exact problem.
- **Failures are task states, not exceptions.** An agent crash becomes a `failed` task with the error message, so the orchestrator can report which agent failed instead of crashing.
- **Ask instead of guess.** A request with no identifiable topic ends as `input-required`, so no searches or writing are spent on a guess.
- **Swappable agents, proven by tests.** The offline tests run the same orchestrator against stub agents that publish the same skills. Replacing the stubs with the real agents changes nothing in the orchestrator.

## Tests

The test suite needs no API keys. Stub agents with the same skills run on real A2A servers, and the LLM and web search are replaced by fakes:

```bash
pytest
```

| File | What it checks |
|---|---|
| `test_protocol.py` | Agent Cards at the well-known path, discovery by skill, `message/send`, `input-required` and `failed` tasks, `contextId`, `tasks/get`, JSON-RPC errors, an unreachable agent |
| `test_orchestrator.py` | A full run, stopping for clarification, reporting a failing agent by name, one `contextId` per run |
| `test_agents.py` | The extractor's brief and clarification path, the Researcher's source check, the Writer's citation check and retry |

The notebooks run the same kind of offline tests in their Step 6.

## Run it

**In Google Colab (notebooks):**

1. Open a notebook from `notebooks/` in Colab.
2. Add `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`) and `TAVILY_API_KEY` under **Secrets** (🔑) with notebook access on.
3. Run Step 1 (install), restart the session if Colab asks, then run all cells. Set `PROVIDER` in Step 7 to switch to Claude.

The SDK notebook uses top-level `await` in its cells, which Colab and Jupyter support.

**From the command line (package):**

```bash
pip install -r requirements.txt
pip install -e .                 # makes the a2a_research package importable
cp .env.example .env             # then add your keys
```

Ask a question, with all three agents started in one process:

```bash
python -m a2a_research.main "What are the latest trends in GenAI for enterprise?"
```

Or run each agent as its own service, the way they'd be deployed, and point the orchestrator at them:

```bash
python -m a2a_research.serve extractor  --port 10001   # terminal 1
python -m a2a_research.serve researcher --port 10002   # terminal 2
python -m a2a_research.serve writer     --port 10003   # terminal 3

python -m a2a_research.main "What are the latest trends in GenAI for enterprise?" \
    --agents http://127.0.0.1:10001 http://127.0.0.1:10002 http://127.0.0.1:10003
```

The orchestrator only receives URLs. It reads each Agent Card and finds the agents by skill, so they could be on different machines or written in other languages.

**Stack:** A2A protocol (JSON-RPC 2.0 over HTTP) · LangGraph · LangChain · CrewAI · Tavily · OpenAI or Anthropic

## What I'd add next

- **Containers and authentication:** a Dockerfile per agent, with an authentication scheme declared in each Agent Card.
- **Interoperability:** connect the orchestrator to an A2A agent written by someone else, in another language.
- **Timeouts and cancellation:** use the streamed updates to detect a stuck agent and cancel its task.
- **An evaluation set** of questions to measure answer quality and how often findings are dropped by the source check.

*Built from a course demo in which LangGraph called three agents as in-process Python functions on Azure OpenAI. Rebuilt so the agents communicate over the actual A2A protocol, with Agent Cards, skill-based discovery, task states, source and citation checks, provider choice (OpenAI or Anthropic), a command-line package and a test suite.*
