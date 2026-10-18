"""Ask a research question.

Run everything in one process (each agent on its own local port):
    python -m a2a_research.main "What are the latest trends in GenAI for enterprise?"

Or connect to agents already running as separate services (see serve.py):
    python -m a2a_research.main "..." --agents http://127.0.0.1:10001 http://127.0.0.1:10002 http://127.0.0.1:10003

The orchestrator only needs URLs: it reads each Agent Card and finds agents by skill.
"""
import argparse

from .config import get_settings, require_keys
from .orchestrator import build_orchestrator, run
from .protocol import A2AServer, AgentDirectory


def start_local_agents() -> list[A2AServer]:
    from .agents import AGENT_FUNCTIONS
    from .skills import AGENT_SPECS, agent_card
    return [A2AServer(agent_card(name), AGENT_FUNCTIONS[name]).start() for name in AGENT_SPECS]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Multi-agent research over A2A.")
    parser.add_argument("question")
    parser.add_argument("--agents", nargs="+", metavar="URL",
                        help="base URLs of running agents; if omitted, all three start in this process")
    args = parser.parse_args(argv)

    servers = []
    if args.agents:
        urls = args.agents
    else:
        require_keys()
        servers = start_local_agents()
        urls = [s.url for s in servers]

    try:
        directory = AgentDirectory()
        for url in urls:
            directory.register(url)
        settings = get_settings()
        print(f"Model: {settings.provider} / {settings.model}\nAgents:")
        directory.show()
        print()
        run(build_orchestrator(directory), args.question)
    finally:
        for s in servers:
            s.stop()


if __name__ == "__main__":
    main()
