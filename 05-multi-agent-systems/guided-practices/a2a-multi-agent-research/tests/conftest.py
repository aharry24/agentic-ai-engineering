"""Stub A2A agents with the same skills as the real ones. No LLM, no API keys."""
import pytest

from a2a_research.protocol import A2AServer, AgentDirectory, AgentReply, make_agent_card
from a2a_research.skills import EXTRACT_SKILL, RESEARCH_SKILL, WRITE_SKILL


def stub_extractor(text, data):
    if len(text.split()) < 3:
        return AgentReply(state="input-required", text="What topic should I research?")
    return AgentReply(text="Research: " + text, data={"task": text, "search_queries": [text], "audience": "general"})


def stub_researcher(text, data):
    if "crash" in text:
        raise RuntimeError("search service unavailable")
    return AgentReply(text="2 findings", data={"findings": [
        {"point": "Finding one", "source_url": "https://example.com/a"},
        {"point": "Finding two", "source_url": "https://example.com/b"}]})


def stub_writer(text, data):
    urls = [f["source_url"] for f in data["findings"]]
    return AgentReply(text="Answer", data={"answer": "Finding one [1]. Finding two [2].", "sources": urls})


@pytest.fixture(scope="session")
def stubs():
    servers = [A2AServer(make_agent_card("Stub Extractor", "Test double", [EXTRACT_SKILL]), stub_extractor).start(),
               A2AServer(make_agent_card("Stub Researcher", "Test double", [RESEARCH_SKILL]), stub_researcher).start(),
               A2AServer(make_agent_card("Stub Writer", "Test double", [WRITE_SKILL]), stub_writer).start()]
    yield servers
    for s in servers:
        s.stop()


@pytest.fixture(scope="session")
def directory(stubs):
    d = AgentDirectory()
    for s in stubs:
        d.register(s.url)
    return d
