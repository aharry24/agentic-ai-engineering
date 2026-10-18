"""Run one agent as a standalone A2A server, the way it would be deployed.

    python -m a2a_research.serve extractor  --port 10001
    python -m a2a_research.serve researcher --port 10002
    python -m a2a_research.serve writer     --port 10003

Each prints its Agent Card URL and serves until stopped with Ctrl+C.
"""
import argparse

from .agents import AGENT_FUNCTIONS
from .config import require_keys
from .protocol import CARD_PATH, A2AServer
from .skills import AGENT_SPECS, agent_card


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Serve one agent over A2A.")
    parser.add_argument("agent", choices=sorted(AGENT_SPECS))
    parser.add_argument("--host", default="127.0.0.1", help="interface to bind (use 0.0.0.0 inside a container)")
    parser.add_argument("--port", type=int, default=0, help="0 picks a free port")
    parser.add_argument("--public-url", default=None, help="URL other agents should use, if different from host:port")
    args = parser.parse_args(argv)

    require_keys()
    server = A2AServer(agent_card(args.agent), AGENT_FUNCTIONS[args.agent], args.host, args.port, args.public_url)
    print(f"{server.card['name']} serving at {server.url}  (Agent Card: {server.url.rstrip('/')}{CARD_PATH})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
