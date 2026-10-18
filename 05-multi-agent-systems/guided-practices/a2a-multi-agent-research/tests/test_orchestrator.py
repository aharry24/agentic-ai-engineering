"""The LangGraph orchestrator, run against stub A2A agents."""
from a2a_research.orchestrator import build_orchestrator, run
from a2a_research.protocol import WIRE_LOG


def test_completed_run_calls_all_three_skills(directory):
    WIRE_LOG.clear()
    result = run(build_orchestrator(directory), "Summarize GenAI trends for enterprise", show=False)
    assert result["status"] == "completed"
    assert result["answer"] == "Finding one [1]. Finding two [2]."
    assert result["sources"] == ["https://example.com/a", "https://example.com/b"]
    assert [t["skill"] for t in result["trace"]] == ["extract_research_brief", "web_research", "write_cited_answer"]
    context_ids = {e["request"]["params"]["message"]["contextId"] for e in WIRE_LOG}
    assert len(context_ids) == 1                                   # one contextId for the whole run


def test_input_required_stops_after_the_first_agent(directory):
    result = run(build_orchestrator(directory), "trends", show=False)
    assert result["status"] == "input-required"
    assert result["message"] == "Stub Extractor: What topic should I research?"
    assert len(result["trace"]) == 1


def test_failing_agent_is_reported_by_name(directory):
    result = run(build_orchestrator(directory), "please crash the research step", show=False)
    assert result["status"] == "failed"
    assert result["message"].startswith("Stub Researcher:")
    assert [t["state"] for t in result["trace"]] == ["completed", "failed"]
