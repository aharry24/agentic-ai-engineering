# 04 · LLM Internals & Planning Systems

Prompting strategies that make LLMs reason and plan (chain-of-thought, ReAct), and turning them into agents grounded in custom knowledge and tools.

## Course-end project

| Project | Summary |
|---|---|
| [RAG Pipeline: PDF Chunking & Retrieval](projects/rag-pipeline-pdf-chunking) | Loads Uber and Lyft SEC filings, chunks and embeds them with OpenAI, indexes them in FAISS, and answers questions with retrieved context |

## Demos

| Demo | Summary |
|---|---|
| [Feature Prioritization Agent](demos/feature-prioritization-agent) | An orchestrator agent consults three stakeholder agents (User Advocate, Tech Lead, Business Analyst), whose scores are Pydantic-validated and must cite real evidence. The ranking, a sensitivity check across four weightings, and disagreement flags are computed in code, not by the LLM. Built on a hand-written tool-calling loop with parallel tool calls, error recovery and offline tests |
| [RAG-Powered FAQ Agent](demos/rag-faq-agent) | Answers questions from a custom FAQ knowledge base using Azure OpenAI embeddings, FAISS and a RetrievalQA chain |
| [Finance Q&A Agent](demos/finance-qa-agent-langchain) | A LangChain agent that answers finance questions and runs Python for the calculations |

**Skills:** chain-of-thought and ReAct prompting · RAG · FAISS · LangChain agents and tool calling · multi-agent orchestration · structured outputs with Pydantic validation · deterministic scoring and guardrails · offline testing with scripted LLMs · OpenAI, Anthropic and Azure OpenAI
