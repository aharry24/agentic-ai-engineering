"""The agents' own logic and checks, with the LLM and web search replaced by fakes."""
from a2a_research.agents import extractor, researcher, writer
from a2a_research.agents.extractor import ResearchBrief
from a2a_research.agents.researcher import Finding


# ---------- Task Extractor ----------
class FakeChain:
    def __init__(self, brief):
        self.brief = brief

    def invoke(self, _):
        return self.brief


def brief(**overrides):
    values = {"task": "Research GenAI trends", "search_queries": ["genai trends", " ", "q2", "q3"],
              "audience": "enterprise leaders", "needs_clarification": False, "clarifying_question": ""}
    return ResearchBrief(**{**values, **overrides})


def test_extractor_returns_a_brief_with_at_most_three_queries(monkeypatch):
    monkeypatch.setattr(extractor, "get_chain", lambda: FakeChain(brief()))
    reply = extractor.task_extractor("anything", None)
    assert reply.state == "completed"
    assert reply.data["search_queries"] == ["genai trends", "q2", "q3"]       # blank query dropped, capped at 3


def test_extractor_asks_when_the_request_is_too_vague(monkeypatch):
    monkeypatch.setattr(extractor, "get_chain",
                        lambda: FakeChain(brief(needs_clarification=True, clarifying_question="Which topic?")))
    reply = extractor.task_extractor("look into it", None)
    assert reply.state == "input-required" and reply.text == "Which topic?"


# ---------- Researcher: the source check ----------
def test_keep_sourced_drops_findings_with_invented_urls():
    findings = [Finding(point="real", source_url="https://site.com/page/"),
                Finding(point="invented", source_url="https://made-up.com")]
    kept = researcher.keep_sourced(findings, ["https://SITE.com/page"])        # case and trailing slash ignored
    assert [f["point"] for f in kept] == ["real"]


def test_researcher_fails_when_no_finding_is_sourced(monkeypatch):
    monkeypatch.setattr(researcher, "_run_crew",
                        lambda brief: ([Finding(point="x", source_url="https://made-up.com")], ["https://real.com"]))
    reply = researcher.researcher("task", {"task": "task", "search_queries": ["q"]})
    assert reply.state == "failed"


def test_researcher_reports_dropped_findings(monkeypatch):
    findings = [Finding(point="a", source_url="https://real.com"), Finding(point="b", source_url="https://fake.com")]
    monkeypatch.setattr(researcher, "_run_crew", lambda brief: (findings, ["https://real.com"]))
    reply = researcher.researcher("task", {"task": "task", "search_queries": ["q"]})
    assert reply.state == "completed" and reply.data["dropped"] == 1 and len(reply.data["findings"]) == 1


# ---------- Writer: the citation check ----------
FINDINGS = {"task": "t", "findings": [{"point": "A", "source_url": "u1"}, {"point": "B", "source_url": "u2"},
                                      {"point": "C", "source_url": "u1"}]}


def test_citation_problems():
    assert writer.citation_problems("A [1] and B [2].", 2) == []
    assert writer.citation_problems("A [3].", 2) == ["[3] is not a source number (valid: 1–2)"]
    assert writer.citation_problems("No citations.", 2) == ["the answer cites no sources"]


def test_writer_numbers_unique_sources_in_order():
    prompt, sources = writer.build_prompt(FINDINGS)
    assert sources == ["u1", "u2"]
    assert "- C [1]" in prompt


def test_writer_retries_once_with_the_problem(monkeypatch):
    drafts, prompts = iter(["A [1] and B [3].", "A [1] and B [2]."]), []
    monkeypatch.setattr(writer, "call_llm", lambda p: prompts.append(p) or next(drafts))
    reply = writer.writer("t", FINDINGS)
    assert reply.state == "completed" and reply.data["sources"] == ["u1", "u2"]
    assert "[3] is not a source number" in prompts[1]


def test_writer_fails_if_the_retry_is_still_wrong(monkeypatch):
    monkeypatch.setattr(writer, "call_llm", lambda p: "No citations here.")
    assert writer.writer("t", FINDINGS).state == "failed"
