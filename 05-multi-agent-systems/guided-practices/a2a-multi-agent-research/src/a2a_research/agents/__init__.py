"""The three agents. Each is a plain function `(text, data) -> AgentReply`; A2AServer makes it reachable."""
from . import extractor, researcher, writer

AGENT_FUNCTIONS = {
    "extractor": extractor.task_extractor,   # LangChain
    "researcher": researcher.researcher,     # CrewAI + Tavily
    "writer": writer.writer,                 # plain OpenAI / Anthropic SDK
}

__all__ = ["AGENT_FUNCTIONS", "extractor", "researcher", "writer"]
