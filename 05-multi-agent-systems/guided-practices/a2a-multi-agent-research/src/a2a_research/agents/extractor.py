"""Agent 1: Task Extractor (LangChain, structured output).

Turns a request into a validated research brief, or ends its task as `input-required`
with a clarifying question when the request has no identifiable topic.
"""
from functools import lru_cache

from pydantic import BaseModel, Field

from ..config import get_settings
from ..protocol import AgentReply


class ResearchBrief(BaseModel):
    task: str = Field(description="The user's request restated as one clear research task")
    search_queries: list[str] = Field(description="2 or 3 focused web search queries")
    audience: str = Field(description="Who the answer is for, e.g. 'enterprise leaders', or 'general' if not stated")
    needs_clarification: bool = Field(description="True only if the request is too vague to research at all")
    clarifying_question: str = Field(description="The question to ask the user if needs_clarification is true, else an empty string")


SYSTEM_PROMPT = ("You turn a user's request into a research brief for a web researcher. "
                 "Ask for clarification only if the request has no identifiable topic.")


def _chat_model():
    settings = get_settings()
    if settings.provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=settings.model)
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(model=settings.model, max_tokens=2000)


@lru_cache(maxsize=1)
def get_chain():
    """Built on first use, so importing this module doesn't need LangChain or an API key."""
    from langchain_core.prompts import ChatPromptTemplate
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", "{request}")])
    return prompt | _chat_model().with_structured_output(ResearchBrief)


def task_extractor(text: str, data: dict | None) -> AgentReply:
    brief = get_chain().invoke({"request": text})
    if brief.needs_clarification:
        return AgentReply(state="input-required", text=brief.clarifying_question or "Could you say more about what you need?")
    brief.search_queries = [q for q in brief.search_queries if q.strip()][:3] or [brief.task]
    return AgentReply(text=brief.task, data=brief.model_dump())
