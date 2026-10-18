"""Agent 2: Researcher (CrewAI + Tavily web search).

A CrewAI agent searches the web and returns findings with source URLs. Code then checks
every URL against the results the search tool actually returned, and drops the rest.
"""
import os

from pydantic import BaseModel, Field

from ..config import get_settings
from ..protocol import AgentReply


class Finding(BaseModel):
    point: str = Field(description="One specific, factual finding")
    source_url: str = Field(description="The URL of the search result this finding came from")


class ResearchFindings(BaseModel):
    findings: list[Finding]


def _norm(url: str) -> str:
    return url.strip().rstrip("/").lower()


def keep_sourced(findings: list[Finding], seen_urls: list[str]) -> list[dict]:
    """The source check: keep only findings whose URL the search tool really returned."""
    seen = {_norm(u) for u in seen_urls}
    return [f.model_dump() for f in findings if _norm(f.source_url) in seen]


def _run_crew(brief: dict) -> tuple[list[Finding], list[str]]:
    """Run the CrewAI researcher. Returns its findings and every URL its search tool returned."""
    from crewai import LLM, Agent, Crew, Task
    from crewai.tools import BaseTool
    from tavily import TavilyClient

    class SearchInput(BaseModel):
        query: str = Field(description="A web search query")

    class WebSearchTool(BaseTool):
        name: str = "web_search"
        description: str = "Search the web for current information. Returns titles, URLs and snippets."
        args_schema: type[BaseModel] = SearchInput
        seen_urls: list = Field(default_factory=list)

        def _run(self, query: str) -> str:
            results = TavilyClient(api_key=os.environ["TAVILY_API_KEY"]).search(query, max_results=5)["results"]
            self.seen_urls.extend(r["url"] for r in results)
            return "\n\n".join(f"{r['title']}\nURL: {r['url']}\n{r['content'][:600]}" for r in results)

    settings = get_settings()
    search = WebSearchTool()
    agent = Agent(role="Web Researcher",
                  goal="Find current, specific, well-sourced information",
                  backstory="You research with a search tool and never state anything you did not find in a result.",
                  tools=[search], llm=LLM(model=f"{settings.provider}/{settings.model}"),
                  allow_delegation=False, verbose=False)
    job = Task(description=(f"Research this task: {brief['task']}\n"
                            f"Start with these searches: {brief['search_queries']}\n"
                            "Return 5 findings. Each source_url must be copied exactly from a search result."),
               expected_output="5 findings, each with the URL it came from", agent=agent,
               output_pydantic=ResearchFindings)
    result = Crew(agents=[agent], tasks=[job], verbose=False, tracing=False).kickoff()
    output = result.pydantic or ResearchFindings.model_validate_json(result.raw)
    return output.findings, search.seen_urls


def researcher(text: str, data: dict | None) -> AgentReply:
    brief = data or {"task": text, "search_queries": [text]}
    findings, seen_urls = _run_crew(brief)
    kept = keep_sourced(findings, seen_urls)
    dropped = len(findings) - len(kept)
    if not kept:
        return AgentReply(state="failed", text=f"None of the {len(findings)} findings could be traced to a search result.")
    return AgentReply(text=f"{len(kept)} sourced findings ({dropped} dropped: URL not in search results)",
                      data={"findings": kept, "dropped": dropped, "searched_urls": len(set(seen_urls))})
