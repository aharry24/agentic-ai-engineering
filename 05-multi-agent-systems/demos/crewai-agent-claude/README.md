# Grounded Research Crew

A multi-agent research pipeline built with **CrewAI**, **Claude** and **Tavily** that writes short, cited executive summaries from live web search, then **automatically checks the summary against the sources the agents actually retrieved**.

```
Researcher (Claude + web search)  →  Writer (Claude, no tools)  →  Verifier (Python)
        │                                                              ▲
        └──── every retrieved page is logged in SOURCE_LOG ────────────┘
```

## The problem this solves

The first version of this project looked like it worked. It produced a polished summary full of specific statistics and named companies. On review, the search tool had only been passing **titles and URLs** to the agent, never page content. The model filled the gap from its own prior knowledge and presented it as research.

This version treats that as the core engineering problem:

| Fix | How |
|---|---|
| **Grounding** | The search tool returns page excerpts, and every result is logged as ground truth. |
| **Citations** | Every claim must carry a source URL; statistics must be copied exactly. |
| **Least privilege** | The writer has no tools, so it can only use the researcher's sourced notes. |
| **Guardrail** | A CrewAI task guardrail sends the summary back to the writer if it exceeds the word limit. |
| **Verification** | Deterministic checks after the run: word count, a citation on every bullet, every cited URL was really retrieved, every number appears in its cited source. |

The verifier is plain Python on purpose. It doesn't ask the model to grade its own work.

## Example verification output

```
PASS  Bullet 1: cited URL was retrieved         ok
PASS  Bullet 1: numbers found in cited source   ok
FLAG  Bullet 3: cited URL was retrieved         not retrieved: https://...
FLAG  Bullet 3: numbers found in cited source   not found: 90%
```

<!-- After your first run, replace this section with your real summary and verification output. -->

## Run it

**Google Colab:** open `crewai_grounded_research_crew.ipynb`, add `ANTHROPIC_API_KEY` and `TAVILY_API_KEY` under Secrets (key icon in the left sidebar), then run all cells.

**Locally:**

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
export TAVILY_API_KEY=...
jupyter notebook crewai_grounded_research_crew.ipynb
```

Change `TOPIC`, `NUM_FINDINGS`, `MAX_SUMMARY_WORDS` or `MODEL` in the configuration cell to reuse the pipeline for another subject.

## Limitations

- Verification runs against search **excerpts**, not full articles, so it can flag true claims. That's a deliberate bias toward false alarms over missed hallucinations.
- It checks numbers and citations, not whether a sentence's meaning matches its source. A separate entailment check or LLM judge (a different model from the writer) would close that gap.
- Search ranking favors vendor blogs and market-research landing pages, which are weak evidence. A source-quality filter would help.

## Stack

CrewAI · Anthropic Claude (via LiteLLM) · Tavily Search API · Python
