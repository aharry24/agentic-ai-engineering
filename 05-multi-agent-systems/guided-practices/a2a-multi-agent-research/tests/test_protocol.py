"""The A2A layer: discovery, message/send, task states, tasks/get and JSON-RPC errors."""
import json

import pytest

from a2a_research.protocol import (A2A_VERSION, CARD_PATH, INVALID_PARAMS, METHOD_NOT_FOUND, PARSE_ERROR,
                                   TASK_NOT_FOUND, A2AError, fetch_agent_card, send_message, task_data,
                                   task_state, task_text)


def rpc(server, payload):
    return server.handle_rpc(json.dumps(payload).encode())


def test_agent_card_is_served_at_the_well_known_path(stubs):
    card = fetch_agent_card(stubs[0].url)
    assert card["protocolVersion"] == A2A_VERSION
    assert card["url"] == stubs[0].url
    assert [s["id"] for s in card["skills"]] == ["extract_research_brief"]
    assert CARD_PATH == "/.well-known/agent-card.json"


def test_directory_finds_agents_by_skill(directory):
    assert directory.find("web_research")["name"] == "Stub Researcher"
    with pytest.raises(A2AError):
        directory.find("translate")


def test_message_send_returns_a_completed_task_with_text_and_data(stubs):
    task = send_message(stubs[0].url, "GenAI trends for enterprise")
    assert task["kind"] == "task" and task_state(task) == "completed"
    assert task_text(task) == "Research: GenAI trends for enterprise"
    assert task_data(task)["task"] == "GenAI trends for enterprise"


def test_input_required_carries_the_agents_question(stubs):
    task = send_message(stubs[0].url, "trends")
    assert task_state(task) == "input-required"
    assert task_text(task) == "What topic should I research?"
    assert task["status"]["message"]["role"] == "agent"


def test_agent_exception_becomes_a_failed_task(stubs):
    task = send_message(stubs[1].url, "crash please")
    assert task_state(task) == "failed"
    assert "search service unavailable" in task_text(task)


def test_context_id_is_kept(stubs):
    task = send_message(stubs[0].url, "GenAI trends for enterprise", context_id="ctx-123")
    assert task["contextId"] == "ctx-123"


def test_tasks_get(stubs):
    task = send_message(stubs[0].url, "GenAI trends for enterprise")
    found = rpc(stubs[0], {"jsonrpc": "2.0", "id": 1, "method": "tasks/get", "params": {"id": task["id"]}})
    assert found["result"]["id"] == task["id"]
    missing = rpc(stubs[0], {"jsonrpc": "2.0", "id": 2, "method": "tasks/get", "params": {"id": "nope"}})
    assert missing["error"]["code"] == TASK_NOT_FOUND


def test_json_rpc_errors(stubs):
    assert stubs[0].handle_rpc(b"not json")["error"]["code"] == PARSE_ERROR
    assert rpc(stubs[0], {"jsonrpc": "2.0", "id": 1, "method": "tasks/cancelAll"})["error"]["code"] == METHOD_NOT_FOUND
    assert rpc(stubs[0], {"jsonrpc": "2.0", "id": 1, "method": "message/send", "params": {}})["error"]["code"] == INVALID_PARAMS


def test_unreachable_agent_raises_a2a_error():
    with pytest.raises(A2AError):
        send_message("http://127.0.0.1:9/", "hello", timeout=2)
