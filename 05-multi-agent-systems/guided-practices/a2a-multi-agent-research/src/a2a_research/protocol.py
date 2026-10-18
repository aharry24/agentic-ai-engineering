"""The A2A protocol layer, implemented with the Python standard library.

Server: serves an Agent Card and handles JSON-RPC `message/send` and `tasks/get`.
Client: fetches Agent Cards, sends messages, reads Tasks, and finds agents by skill.
"""
import json
import threading
import uuid
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

A2A_VERSION = "0.3.0"
CARD_PATH = "/.well-known/agent-card.json"   # the well-known discovery path in A2A 0.3

# Standard JSON-RPC 2.0 error codes, plus A2A's own
PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS = -32700, -32600, -32601, -32602
TASK_NOT_FOUND = -32001


def new_id() -> str:
    return str(uuid.uuid4())


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- A2A building blocks: parts, messages, skills, Agent Cards ----------
def text_part(text: str) -> dict:
    return {"kind": "text", "text": text}


def data_part(data: dict) -> dict:
    return {"kind": "data", "data": data}       # structured JSON another agent can use directly


def make_message(role: str, parts: list, context_id: str | None = None, task_id: str | None = None) -> dict:
    message = {"kind": "message", "messageId": new_id(), "role": role, "parts": parts}
    if context_id:
        message["contextId"] = context_id       # groups related tasks into one conversation
    if task_id:
        message["taskId"] = task_id
    return message


def make_skill(skill_id: str, name: str, description: str, tags: list, examples: list = ()) -> dict:
    return {"id": skill_id, "name": name, "description": description, "tags": list(tags), "examples": list(examples)}


def make_agent_card(name: str, description: str, skills: list) -> dict:
    """The agent's public description. `url` is filled in when the server starts."""
    return {
        "protocolVersion": A2A_VERSION,
        "name": name,
        "description": description,
        "url": "",
        "version": "1.0.0",
        "preferredTransport": "JSONRPC",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "defaultInputModes": ["text/plain", "application/json"],
        "defaultOutputModes": ["text/plain", "application/json"],
        "skills": skills,
    }


@dataclass
class AgentReply:
    """What an agent function returns. The server turns it into an A2A Task."""
    state: str = "completed"          # completed | input-required | failed | rejected
    text: str = ""
    data: dict | None = None


def rpc_result(request_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def rpc_error(request_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


# ---------- The server ----------
class A2AServer:
    """Serves one agent over A2A. `agent_fn(text, data) -> AgentReply` is the agent itself."""

    def __init__(self, card: dict, agent_fn, host: str = "127.0.0.1", port: int = 0, public_url: str | None = None):
        """`public_url` is the address other agents should use, if it differs from host:port (e.g. behind a proxy)."""
        self.card, self.agent_fn, self.tasks = card, agent_fn, {}
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):          # keep the notebook output clean
                pass

            def _send(self, status: int, body: dict):
                raw = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):                       # discovery: anyone can read the Agent Card
                if self.path == CARD_PATH:
                    self._send(200, server.card)
                else:
                    self._send(404, {"error": "not found"})

            def do_POST(self):                      # all A2A calls are JSON-RPC POSTs to the agent URL
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                self._send(200, server.handle_rpc(body))

        self.httpd = ThreadingHTTPServer((host, port), Handler)     # port 0 = pick any free port
        self.url = public_url or f"http://{host}:{self.httpd.server_address[1]}/"
        self.card["url"] = self.url
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self):
        self._thread.start()
        return self

    def serve_forever(self):
        """Run in the foreground, for a standalone agent process (see serve.py)."""
        self.httpd.serve_forever()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    # ---- JSON-RPC dispatch ----
    def handle_rpc(self, raw: bytes) -> dict:
        try:
            request = json.loads(raw)
        except json.JSONDecodeError:
            return rpc_error(None, PARSE_ERROR, "Parse error: the body is not valid JSON")
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or "method" not in request:
            return rpc_error(request.get("id") if isinstance(request, dict) else None, INVALID_REQUEST,
                             "Invalid request: expected a JSON-RPC 2.0 object with a method")
        request_id, method, params = request.get("id"), request["method"], request.get("params") or {}
        if method == "message/send":
            return self._message_send(request_id, params)
        if method == "tasks/get":
            task = self.tasks.get(params.get("id"))
            return rpc_result(request_id, task) if task else rpc_error(request_id, TASK_NOT_FOUND, "Task not found")
        return rpc_error(request_id, METHOD_NOT_FOUND, f"Method not found: {method}")

    def _message_send(self, request_id, params: dict) -> dict:
        message = params.get("message")
        if not isinstance(message, dict) or not message.get("parts"):
            return rpc_error(request_id, INVALID_PARAMS, "params.message with at least one part is required")
        text = "\n".join(p.get("text", "") for p in message["parts"] if p.get("kind") == "text")
        data = next((p.get("data") for p in message["parts"] if p.get("kind") == "data"), None)

        # 1. Create the Task. Its lifecycle starts in "working".
        context_id = message.get("contextId") or new_id()
        task = {"kind": "task", "id": new_id(), "contextId": context_id,
                "status": {"state": "working", "timestamp": now()}, "artifacts": [], "history": [message]}
        self.tasks[task["id"]] = task

        # 2. Run the agent. A crash becomes a "failed" task the client can handle.
        try:
            reply = self.agent_fn(text, data)
        except Exception as err:
            reply = AgentReply(state="failed", text=f"{type(err).__name__}: {err}")

        # 3. Record the outcome. A completed task carries its output as an Artifact;
        #    any other state carries an agent Message explaining it (e.g. the clarifying question).
        parts = [text_part(reply.text)] + ([data_part(reply.data)] if reply.data is not None else [])
        if reply.state == "completed":
            task["artifacts"].append({"artifactId": new_id(), "name": "result", "parts": parts})
            task["status"] = {"state": "completed", "timestamp": now()}
        else:
            task["status"] = {"state": reply.state, "timestamp": now(),
                              "message": make_message("agent", parts, context_id, task["id"])}
        return rpc_result(request_id, task)


# =============================== Client ===============================
WIRE_LOG = []


class A2AError(Exception):
    """A JSON-RPC error returned by an agent, or a failure to reach it."""


def _http_json(url: str, body: dict | None = None, timeout: float = 300) -> dict:
    request = urllib.request.Request(
        url, data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except (urllib.error.URLError, TimeoutError) as err:
        raise A2AError(f"could not reach {url}: {err}") from err


def fetch_agent_card(base_url: str) -> dict:
    return _http_json(base_url.rstrip("/") + CARD_PATH)


def send_message(agent_url: str, text: str, data: dict | None = None, context_id: str | None = None,
                 timeout: float = 300) -> dict:
    """Send an A2A message/send request and return the Task."""
    parts = [text_part(text)] + ([data_part(data)] if data is not None else [])
    request = {"jsonrpc": "2.0", "id": new_id(), "method": "message/send",
               "params": {"message": make_message("user", parts, context_id)}}
    response = _http_json(agent_url, request, timeout)
    WIRE_LOG.append({"agent_url": agent_url, "request": request, "response": response})
    if "error" in response:
        raise A2AError(f"JSON-RPC error {response['error']['code']}: {response['error']['message']}")
    return response["result"]


# ---------- Reading a Task ----------
def task_state(task: dict) -> str:
    return task["status"]["state"]


def task_parts(task: dict) -> list:
    """Output parts: the artifacts of a completed task, or the status message of any other state."""
    if task.get("artifacts"):
        return [part for artifact in task["artifacts"] for part in artifact["parts"]]
    return (task["status"].get("message") or {}).get("parts", [])


def task_text(task: dict) -> str:
    return "\n".join(p["text"] for p in task_parts(task) if p["kind"] == "text")


def task_data(task: dict) -> dict | None:
    return next((p["data"] for p in task_parts(task) if p["kind"] == "data"), None)


# ---------- Discovery ----------
class AgentDirectory:
    """Knows agents only through their Agent Cards, and finds them by skill ID."""

    def __init__(self):
        self.cards = []

    def register(self, base_url: str) -> dict:
        card = fetch_agent_card(base_url)
        self.cards = [c for c in self.cards if c["url"] != card["url"]] + [card]
        return card

    def find(self, skill_id: str) -> dict:
        for card in self.cards:
            if any(s["id"] == skill_id for s in card["skills"]):
                return card
        raise A2AError(f"no registered agent offers the skill '{skill_id}'")

    def show(self):
        for card in self.cards:
            skills = ", ".join(s["id"] for s in card["skills"])
            print(f"  {card['name']:<16} {card['url']:<26} skills: {skills}")
