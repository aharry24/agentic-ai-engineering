"""Agent 3: Writer (plain OpenAI / Anthropic SDK, no agent framework).

Writes the final answer with numbered citations. Code checks every citation; a bad draft
gets one retry with the exact problem, then the task fails.
"""
import re

from ..config import get_settings
from ..protocol import AgentReply

CITATION_RE = re.compile(r"\[(\d+)\]")


def call_llm(prompt: str) -> str:
    settings = get_settings()
    if settings.provider == "openai":
        from openai import OpenAI
        reply = OpenAI().chat.completions.create(model=settings.model, messages=[{"role": "user", "content": prompt}])
        return reply.choices[0].message.content or ""
    import anthropic
    reply = anthropic.Anthropic().messages.create(model=settings.model, max_tokens=2000,
                                                  messages=[{"role": "user", "content": prompt}])
    return "".join(block.text for block in reply.content if block.type == "text")


def citation_problems(answer: str, n_sources: int) -> list[str]:
    cited = {int(n) for n in CITATION_RE.findall(answer)}
    problems = [f"[{n}] is not a source number (valid: 1–{n_sources})" for n in sorted(cited) if not 1 <= n <= n_sources]
    if not cited:
        problems.append("the answer cites no sources")
    return problems


def build_prompt(data: dict) -> tuple[str, list[str]]:
    findings = data["findings"]
    sources = list(dict.fromkeys(f["source_url"] for f in findings))          # unique, in order
    numbered = "\n".join(f"- {f['point']} [{sources.index(f['source_url']) + 1}]" for f in findings)
    prompt = (f"Task: {data['task']}\nAudience: {data.get('audience', 'general')}\n\n"
              f"Findings, with source numbers:\n{numbered}\n\n"
              "Write a concise answer (one short paragraph plus up to 5 bullet points) using ONLY these findings. "
              "Cite source numbers in square brackets, e.g. [1]. Do not add facts that are not in the findings.")
    return prompt, sources


def writer(text: str, data: dict | None) -> AgentReply:
    prompt, sources = build_prompt(data)
    answer = call_llm(prompt)
    problems = citation_problems(answer, len(sources))
    if problems:                                                             # one retry with the exact problem
        answer = call_llm(prompt + f"\n\nYour previous draft had problems: {'; '.join(problems)}. Rewrite it.")
        problems = citation_problems(answer, len(sources))
    if problems:
        return AgentReply(state="failed", text="Citation check failed: " + "; ".join(problems))
    return AgentReply(text=answer, data={"answer": answer, "sources": sources})
