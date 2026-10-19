# Project Report: Building a RAG Pipeline Using PDF Chunking and Retrieval

## 1. Introduction

**Objective.** Build the retrieval core of an AI document assistant. It should take long PDF documents, split them into searchable chunks, embed them with OpenAI, index them in FAISS, and return the passages most relevant to a user's question. A GPT model then answers the question grounded in those passages.

**Why RAG matters.** Large language models don't know anything about private or recent documents, and when asked about them they tend to make up plausible-sounding answers. Retrieval-Augmented Generation (RAG) fixes this without retraining the model. When asked a question, the system retrieves the relevant passages from a trusted document collection and passes them to the model as context. The results:

- answers grounded in the actual source text, with page-level citations the user can verify;
- up-to-date knowledge: adding a new document only means embedding it, not fine-tuning;
- efficiency: the model reads a few relevant chunks instead of hundreds of pages, which may exceed its context window anyway.

**Dataset.** Three real, long, publicly filed SEC reports (643 pages in total):

| File | Document |
|---|---|
| uber_2021.pdf | Uber Technologies, Form 10-K (FY 2021) |
| lyft_2021.pdf | Lyft, Inc., Form 10-K (FY 2021) |
| uber_10q_sept_2022.pdf | Uber Technologies, Form 10-Q (Q3 2022) |

Financial filings make a realistic, demanding test. They mix narrative text (risk factors, management discussion) with dense numeric tables, and two companies in the same industry use very similar language.

## 2. Implementation Overview

| Stage | Tool | Configuration |
|---|---|---|
| Environment | VS Code/Google Colab, Python virtual environment, Jupyter notebook, Colab Secrets | `requirements.txt`, API key in `.env` or in Colab Secrets |
| Load | LangChain `PyPDFLoader` | One Document per page, with `source` and `page` metadata |
| Chunk | LangChain `RecursiveCharacterTextSplitter` | chunk_size = 1000 chars, overlap = 200, separators ¶ → line → sentence → word |
| Embed | OpenAI `text-embedding-3-small` via `langchain-openai` | {{EMBED_DIM}}-dimensional vectors, batched 500 per request |
| Store | FAISS (`faiss-cpu`) via LangChain | Flat L2 index, saved to `vectorstore/faiss_index` and reloaded on later runs |
| Retrieve | `similarity_search_with_score` | Top-k nearest chunks; L2 distance converted to cosine similarity |
| Generate | OpenAI `gpt-4o-mini` | Temperature 0; prompt restricts answers to the retrieved context and requires (file, page) citations |

**Flow:** PDFs → pages → chunks → embeddings → FAISS index → query embedding → top-k chunks → GPT answer with citations.

## 3. Metrics

**Chunking results**

| Metric | Value |
|---|---|
| Total pages | **643** |
| Total chunks | **3453** |
| Average chunk size | **863 characters** |
| Min / max chunk size | **55 / 1000 characters** |

| Document | Chunks | Avg. chunk size (chars) |
|---|---|---|
{{PER_DOC_TABLE}}

The average sits a little below the 1,000-character limit. That's expected: the splitter cuts at the last natural boundary (paragraph, line or sentence) before the limit rather than mid-word, and short pages produce short final chunks.

**Sample query output**

- **Query:** What were Uber's total revenues for 2021 and how did they change from 2020?
- **Top match:** Source: *uber_2021.pdf*, page 57, cosine similarity = **0.7574**


Top Chunk:
```
ments— % — % Net loss including non-controlling interests
(61) % (3) % Less: net loss attributab
le to non-controlling interests, net of tax— % — % Net loss attributable to Uber Technologies, Inc.
(61) % (3) %  Totals of percentage of 
revenues may not foot due to rounding.Comparison of the Years Ended December 31, 2020 and 2021
Revenue
Year Ended December 31,
2020 to 2021 % Change
(In millions, except percentages)2020 2021 Revenue
$ 11,139 $ 17,455 57 % 2021
 Compared to 2020 Revenue
 increased $6.3 billion, or 57%, primarily attributable to an increase in Gross Bookings of 56%, or 53% on a constant currency basis. The increase inGross
 Bookings was primarily driven by an increase in Delivery Gross Bookings of 71%, or 66% on a constant currency basis, due to an increase in food deliveryorders
 and  higher  basket  sizes  as  a  result  of  stay-at-home  order  demand  related  to  COVID-19,  as  well  as  continued  expansion  across  U.S.  and  internationalmarkets.
```

**GPT answer generated from the retrieved chunks:**

> *Uber's total revenues for 2021 were $17,455 million, which represented a 57% increase from 2020, where revenues were $11,139 million (uber_2021.pdf, page 57).*

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
