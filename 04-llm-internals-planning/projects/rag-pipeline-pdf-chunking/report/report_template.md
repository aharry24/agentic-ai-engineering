# Project Report: Building a RAG Pipeline Using PDF Chunking and Retrieval

## 1. Introduction

**Objective.** Build the retrieval core of an AI document assistant. It should take long PDF documents, split them into searchable chunks, embed them with OpenAI, index them in FAISS, and return the passages most relevant to a user's question. A GPT model then answers the question grounded in those passages.

**Why RAG matters.** Large language models don't know anything about private or recent documents, and when asked about them they tend to make up plausible-sounding answers. Retrieval-Augmented Generation (RAG) fixes this without retraining the model. At question time the system retrieves the relevant passages from a trusted document collection and passes them to the model as context. The results:

- answers grounded in the actual source text, with page-level citations the user can verify;
- up-to-date knowledge: adding a new document only means embedding it, not fine-tuning;
- efficiency: the model reads a few relevant chunks instead of hundreds of pages, which would exceed its context window anyway.

**Dataset.** Three real, long, publicly filed SEC reports ({{PAGES}} pages in total):

| File | Document |
|---|---|
| uber_2021.pdf | Uber Technologies, Form 10-K (FY 2021) |
| lyft_2021.pdf | Lyft, Inc., Form 10-K (FY 2021) |
| uber_10q_sept_2022.pdf | Uber Technologies, Form 10-Q (Q3 2022) |

Financial filings make a realistic, demanding test. They mix narrative text (risk factors, management discussion) with dense numeric tables, and two companies in the same industry use very similar language.

## 2. Implementation Overview

| Stage | Tool | Configuration |
|---|---|---|
| Environment | VS Code, Python virtual environment, Jupyter notebook | `requirements.txt`, API key in `.env` |
| Load | LangChain `PyPDFLoader` | One Document per page, with `source` and `page` metadata |
| Chunk | LangChain `RecursiveCharacterTextSplitter` | chunk_size = 1000 chars, overlap = 200, separators ¶ → line → sentence → word |
| Embed | OpenAI `{{EMBEDDING_MODEL}}` via `langchain-openai` | {{EMBED_DIM}}-dimensional vectors, batched 500 per request |
| Store | FAISS (`faiss-cpu`) via LangChain | Flat L2 index, saved to `vectorstore/faiss_index` and reloaded on later runs |
| Retrieve | `similarity_search_with_score` | Top-k nearest chunks; L2 distance converted to cosine similarity |
| Generate | OpenAI `{{CHAT_MODEL}}` | Temperature 0; prompt restricts answers to the retrieved context and requires (file, page) citations |

**Flow:** PDFs → pages → chunks → embeddings → FAISS index → query embedding → top-k chunks → GPT answer with citations.

## 3. Metrics

**Chunking results**

| Metric | Value |
|---|---|
| Total pages | {{PAGES}} |
| Total chunks | **{{TOTAL_CHUNKS}}** |
| Average chunk size | **{{AVG_CHUNK_SIZE}} characters** |
| Min / max chunk size | {{MIN_CHUNK}} / {{MAX_CHUNK}} characters |

| Document | Chunks | Avg. chunk size (chars) |
|---|---|---|
{{PER_DOC_TABLE}}

The average sits a little below the 1,000-character limit. That's expected: the splitter cuts at the last natural boundary (paragraph, line or sentence) before the limit rather than mid-word, and short pages produce short final chunks.

**Sample query output**

- **Query:** {{SAMPLE_QUERY}}
- **Top match:** {{TOP_SOURCE}} (cosine similarity {{TOP_SCORE}})

```
{{TOP_CHUNK}}
```

**GPT answer generated from the retrieved chunks:**

> {{GPT_ANSWER}}

More queries, with their top-3 matches and answers, are in `outputs/sample_outputs.md`.

## 4. Conclusion

**Insights gained**

- Chunking choices directly shape retrieval quality. With 1,000-character chunks and 200 overlap, most chunks hold one coherent idea: a risk factor, a paragraph of management discussion, or a small table. Small enough to match precisely, big enough to give the model useful context.
- Semantic search matches meaning, not keywords. A question about drivers being "classified as employees" finds the relevant risk-factor text even when the wording differs.
- Page-level metadata makes every answer traceable back to the source filing, which matters for trust.
- Saving the FAISS index to disk means embeddings are paid for once. Later queries only embed the short question.

**Issues faced**

- **Tables.** `pypdf` flattens financial tables into plain text, so a number can end up in a different chunk from its row or column label. Numeric questions are therefore harder than narrative ones.
- **Similar documents.** Uber and Lyft filings share a lot of vocabulary, so a question about one company can pull a chunk from the other.
- **Boilerplate.** Cover pages, tables of contents and legal notices produce low-value chunks. Very short chunks (under 50 characters) were filtered out.
- **Cost and rate limits.** Embedding thousands of chunks is cheap with `text-embedding-3-small`, but it has to be batched to stay inside API rate limits.

**Possible improvements**

- Metadata filtering (e.g. restrict by `source` or company) and adding the company name and section title to each chunk.
- Hybrid search (BM25 keyword + vector) and a re-ranker (e.g. a cross-encoder) to improve precision on numeric and exact-term queries.
- Table-aware parsing (e.g. `pdfplumber`, `unstructured`, or a layout model) so tables are chunked as whole units.
- Tuning chunk size and overlap and measuring the effect with a small labelled question set (hit-rate@k, MRR).
- Maximal Marginal Relevance (MMR) retrieval to reduce near-duplicate chunks in the top-k.
- A simple chat UI (e.g. Streamlit) with conversation memory to turn the pipeline into a usable assistant.
