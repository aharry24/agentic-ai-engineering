# 03 · Generative AI Tech Stack & Prompt Engineering

The orchestration and application layers of the agentic AI stack: how different frameworks model multi-step agent workflows, and how agentic RAG decides where to look for an answer.

## Demos

| Demo | Summary |
|---|---|
| [Analyst → Strategist, three frameworks](demos/analyst-strategist-multi-framework) | One two-agent workflow built in **LangGraph** (explicit state graph), **CrewAI** (role-based crew) and **Microsoft Agent Framework**, to compare how each defines flow and hand-offs |
| [Agentic RAG with Claude](demos/agentic-rag-anthropic) | A router–retriever RAG system on Claude, with Docling PDF parsing, local Hugging Face embeddings and ChromaDB, so it needs no OpenAI key |

**Skills:** LangGraph · CrewAI · Microsoft Agent Framework · agentic RAG · Anthropic API
