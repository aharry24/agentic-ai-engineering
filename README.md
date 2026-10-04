# Agentic AI Engineering

Hands-on work from a 12-module Agentic AI program: Python foundations, LLM internals, RAG, multi-agent systems (LangGraph, CrewAI, AutoGen), the Model Context Protocol, and deploying agents to production.

Every folder contains code I ran, adapted and documented myself, plus a course-end project for each module where one applies.

**Alron Harry** · Business Insights / Data Analyst · M.S. Data Science
[LinkedIn](https://www.linkedin.com/in/alron-harry/) · [GitHub](https://github.com/aharry24)

---

## Featured projects

| Project | What it does | Stack |
|---|---|---|
| [Agentic RAG: Router–Retriever](05-multi-agent-systems/projects/agentic-rag-router-retriever) | A router agent sends each question to a PDF knowledge base, live web search, or the LLM directly; a retriever agent returns a grounded, cited answer | CrewAI, Tavily, PDF search, Pydantic |
| [RAG Pipeline: PDF Chunking & Retrieval](04-llm-internals-planning/projects/rag-pipeline-pdf-chunking) | Loads long SEC filings (Uber, Lyft), chunks and embeds them, and answers questions with semantic search | OpenAI embeddings, FAISS, LangChain |
| [Multi-Framework Analyst → Strategist](03-genai-stack-prompt-engineering/demos/analyst-strategist-multi-framework) | The same two-agent workflow built three ways, to compare orchestration styles | LangGraph, CrewAI, Microsoft Agent Framework |
| [Agent-to-Agent (A2A) Collaboration](05-multi-agent-systems/guided-practices/google-a2a-multi-framework) | LangChain, CrewAI and a custom OpenAI agent passing work to each other inside one LangGraph graph | LangGraph, A2A, Azure OpenAI |

## Repository map

| # | Module | Topics |
|---|---|---|
| 01 | [Python Foundations](01-python-foundations) | Data structures, OOP, file and error handling, AI pair-programming with Copilot |
| 02 | [Foundations of AI & Agentic AI](02-ai-agentic-foundations) | ML → deep learning → transformers → LLMs → agents |
| 03 | [GenAI Tech Stack & Prompt Engineering](03-genai-stack-prompt-engineering) | Agent orchestration frameworks, agentic RAG |
| 04 | [LLM Internals & Planning Systems](04-llm-internals-planning) | CoT and ReAct prompting, RAG agents, tool-using agents |
| 05 | [Multi-Agent Systems](05-multi-agent-systems) | CrewAI, LangGraph, A2A protocol, serial/parallel workflows |
| 06 | Multi-Agent Systems II | AutoGen, n8n |
| 07 | Model Context Protocol | MCP servers, MCP in n8n |
| 08–12 | Metrics & ROI · Agentic UX · Dev tools · Azure AI agents · Capstone | TBD |

Certificates for completed modules are in [`certificates/`](certificates).

## Tech stack

**Languages:** Python 

**Agent frameworks:** LangGraph, CrewAI, LangChain, Microsoft Agent Framework, AutoGen 

**LLMs:** OpenAI / Azure OpenAI, Anthropic Claude 

**Retrieval:** FAISS, Chroma, OpenAI and Hugging Face embeddings 

**Tools:** Tavily web search, MCP, n8n 

**Environment:** Jupyter, Google Colab, VS Code


## Run it locally

```bash
git clone https://github.com/aharry24/agentic-ai-engineering.git
cd agentic-ai-engineering
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # projects with their own requirements.txt: install from that one
cp .env.example .env               # then add your own API keys
```

Notebooks read API keys from `.env` with `python-dotenv`. No keys are stored in this repo. In Google Colab, add the same keys under **Secrets** instead.

## Acknowledgements

Some demos and guided practices began from starter material provided by the Virginia Tech Applied Agentic AI: Systems Design & Impact program. In each case I ran, extended and documented the code. All course-end projects are my own work. Slides and other proprietary course content are not included in this repo.
