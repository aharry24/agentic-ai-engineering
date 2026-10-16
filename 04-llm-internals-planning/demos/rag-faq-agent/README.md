# RAG-Powered FAQ Agent

A customer-support agent that answers questions from a company FAQ using retrieval-augmented generation. It cites the entry behind every answer, declines questions the FAQ doesn't cover, and masks personal data before it reaches retrieval or the LLM. An evaluation scorecard measures how well it does each of these.

**Notebook:** [`rag_faq_agent.ipynb`](rag_faq_agent.ipynb). It runs on an OpenAI or Anthropic API key. Embeddings run locally, and the offline tests need no key.

## Results

**17 of 18** labelled questions passed in the saved run (gpt-5-mini, Google Colab).

| Question type | Count | What it tests |
|---|---|---|
| Paraphrase | 9 | Different wording from the FAQ: "Can I send back something I bought?" |
| Detail | 4 | The answer depends on a detail: an *opened* item, an order placed 3 hours ago |
| Out of scope | 4 | Not in the FAQ, so the agent must decline instead of guessing |
| PII | 1 | An email and card number in the question are masked, and the answer is still correct |

Each question is scored on retrieval, the refusal decision, answer correctness, citations and PII masking.

**The one failure was a false refusal.** "How do I find out where my package is?" scored a similarity of 0.31 against the order-tracking entry, below the calibrated threshold, so the agent declined a question it could have answered. Every out-of-scope question was correctly refused. For customer support this is the safer mistake: the customer is sent to a person instead of getting a wrong answer. Possible fixes are in [What I'd add next](#what-id-add-next).

## How it works

```
Question
   │
   ├─ 1. mask_pii ── emails, phone numbers, card numbers (Luhn-checked) → [EMAIL] [PHONE] [CARD]
   │
   ├─ 2. retrieve ── local MiniLM embeddings → FAISS → top 3 FAQ entries with cosine similarity
   │
   ├─ 3. should_abstain ── best similarity < threshold? → decline, no LLM call
   │
   ├─ 4. LLM answers from the retrieved entries only, citing them as [FAQ-xx]
   │
   └─ 5. check_citations ── every cited ID must have been retrieved
```

| Component | What it does |
|---|---|
| **One chunk per FAQ entry** | The FAQ is parsed into its question–answer pairs, each with an ID (`FAQ-05`). A character-based splitter could separate a question from its answer; this can't, and every answer can cite exactly one entry. The parser handles Windows line endings and multi-line answers. |
| **Refusal decided in code** | If no entry is similar enough, the agent declines **without calling the LLM**: no cost and no chance of a made-up answer. |
| **Calibrated threshold** | The threshold is set from a separate calibration set of in-scope and out-of-scope questions, at the midpoint between the weakest in-scope match and the strongest out-of-scope match. It is not tuned on the evaluation questions, so the scorecard stays a fair test. If the two groups overlap, the notebook reports that no threshold can separate them perfectly. |
| **PII masking** | Card numbers are masked only if they pass the Luhn check, and phone numbers must have 10–12 digits. An order number like `1234567890123` is left alone instead of being mistaken for a card or a phone number. |
| **Citation check** | An answer that cites an entry that wasn't retrieved is flagged as a hallucinated source. |

## Design decisions

- **Code decides whether to answer; the LLM decides what to say.** Refusing on a similarity score is deterministic, testable and free. A prompt instruction like "say you don't know" is only a request.
- **Local embeddings.** `all-MiniLM-L6-v2` runs in the notebook, so there's no embedding API key, cost or rate limit. The course version used Azure OpenAI.
- **Exact similarity scores.** Embeddings are normalised, so the dot product is the cosine similarity. The score used for refusal is computed directly instead of relying on the vector store's distance metric.
- **Failures are diagnosed by stage.** A retrieval miss, a wrong answer from the right entry, and a wrong refusal point to different fixes: the chunk text, the prompt, or the threshold.

## Offline tests

Step 4 runs without an API key or model download:

1. Parsing produces one entry per Q/A pair, with CRLF and multi-line answers handled.
2. A card number, email and phone number are masked; an order number is not.
3. Below-threshold questions are declined, and overlapping calibration groups are detected.
4. A citation to an entry that wasn't retrieved is caught.
5. Scoring grades answers, refusals, citations and PII correctly.

## Run it

1. Open the notebook in Google Colab.
2. Add `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` under **Secrets** (🔑) with notebook access on, and set `PROVIDER` in Step 6.
3. Upload [`faq.txt`](faq.txt) to the Colab file browser.
4. Run all cells. Without a key, Steps 1–4 still run the offline tests.

**Stack:** LangChain · sentence-transformers (`all-MiniLM-L6-v2`) · FAISS · OpenAI or Anthropic

## What I'd add next

- **Fix the false refusal:** add alternative phrasings to each entry's indexed text, or use hybrid keyword + vector search so a word like "package" can match the tracking entry.
- **A larger calibration set**, so the threshold rests on more than a handful of questions.
- **Conversation history** for follow-up questions, and **tools** such as opening a support ticket when the agent declines.

*Built from a course demo (Azure OpenAI embeddings with a RetrievalQA chain) and extended with per-entry chunking, code-based refusal with a calibrated threshold, PII masking, citation checks, an evaluation scorecard and offline tests.*
