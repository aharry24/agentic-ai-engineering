# 05 · Multi-Agent Systems (I)

Designing systems in which several specialized agents collaborate, covering role-based crews, graph-based workflows, serial versus parallel execution, and agent-to-agent communication across frameworks.

## Course-end project

| Project | Summary | Status |
|---|---|---|
| [Agentic RAG: Router–Retriever](projects/agentic-rag-router-retriever) | A router agent picks PDF search, web search or a direct LLM answer; a retriever agent returns a grounded, cited answer | In progress |

## Guided practice

| Practice | Summary | Status |
|---|---|---|
| [A2A Multi-Framework Collaboration](guided-practices/google-a2a-multi-framework) | LangChain (task extraction) → CrewAI (web research) → custom OpenAI agent (synthesis), orchestrated in LangGraph | In progress |

## Demos

| Demo | Summary | Status |
|---|---|---|
| [CrewAI Agent with Claude](demos/crewai-agent-claude) | A CrewAI agent running on Anthropic's Claude | In progress |
| [AI Product Team in Python](demos/ai-product-team) | A team of specialist agents passing documents downstream, with token and latency tracking | In progress |
| [CrewAI Agent with Web Search](demos/crewai-agent-web-search) | A CrewAI agent with a custom Tavily web-search tool | In progress |
| [Serial & Parallel CrewAI Workflows](demos/crewai-serial-parallel-workflows) | Compares sequential and parallel task execution | In progress |
| [Reactive Agent with LangGraph + Tavily](demos/langgraph-tavily-reactive-agent) | A LangGraph agent that decides when to search the web | In progress |

**Skills:** CrewAI · LangGraph · A2A protocol · Tavily · multi-agent orchestration
