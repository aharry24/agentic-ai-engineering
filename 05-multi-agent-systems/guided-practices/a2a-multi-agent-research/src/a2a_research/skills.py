"""The A2A skills each agent publishes in its Agent Card. The orchestrator finds agents by these IDs."""
from .protocol import make_agent_card, make_skill

EXTRACT_SKILL = make_skill(
    "extract_research_brief", "Extract research brief",
    "Turns a user request into a research task with web search queries, or asks a clarifying question.",
    ["planning", "intent"], ["Summarize the latest GenAI trends for enterprise"])

RESEARCH_SKILL = make_skill(
    "web_research", "Web research",
    "Searches the web and returns findings, each tied to the URL it came from.",
    ["research", "web-search"], ["Recent enterprise GenAI adoption trends"])

WRITE_SKILL = make_skill(
    "write_cited_answer", "Write cited answer",
    "Writes a concise answer for a given audience, citing only the findings it is given.",
    ["writing", "synthesis"])

# name -> (display name, description, skill). Used by serve.py and main.py.
AGENT_SPECS = {
    "extractor": ("Task Extractor", "LangChain agent that turns requests into research briefs", EXTRACT_SKILL),
    "researcher": ("Researcher", "CrewAI agent that researches the web with source-checked findings", RESEARCH_SKILL),
    "writer": ("Writer", "Framework-free agent that writes cited answers", WRITE_SKILL),
}


def agent_card(name: str) -> dict:
    display_name, description, skill = AGENT_SPECS[name]
    return make_agent_card(display_name, description, [skill])
