"""LangGraph orchestrator: an A2A client that discovers agents by skill and routes on task state."""
import operator
import time
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from .protocol import (A2AError, AgentDirectory, make_message, new_id, send_message, task_data,
                       task_state, task_text, text_part)


class ResearchState(TypedDict, total=False):
    question: str
    context_id: str
    brief: dict
    findings: list
    answer: str
    sources: list
    status: str                                   # set when the run stops: completed | input-required | failed
    message: str                                  # the clarifying question or error, if stopped early
    trace: Annotated[list, operator.add]          # each node appends its A2A calls


def build_orchestrator(directory: AgentDirectory):
    def call(skill_id: str, text: str, data: dict | None, state: ResearchState):
        card = directory.find(skill_id)                          # discovery by skill, not by address
        start = time.perf_counter()
        try:
            task = send_message(card["url"], text, data, context_id=state["context_id"])
        except A2AError as err:
            task = {"status": {"state": "failed", "message": make_message("agent", [text_part(str(err))])},
                    "artifacts": []}
        entry = {"agent": card["name"], "skill": skill_id, "state": task_state(task),
                 "seconds": round(time.perf_counter() - start, 1)}
        return task, entry

    def stopped(task, entry) -> dict | None:
        """If the task did not complete, stop the run and pass the agent's message on."""
        if task_state(task) == "completed":
            return None
        return {"status": task_state(task), "message": f"{entry['agent']}: {task_text(task)}", "trace": [entry]}

    def extract(state: ResearchState) -> dict:
        task, entry = call("extract_research_brief", state["question"], None, state)
        return stopped(task, entry) or {"brief": task_data(task), "trace": [entry]}

    def research(state: ResearchState) -> dict:
        brief = state["brief"]
        task, entry = call("web_research", brief["task"], brief, state)
        return stopped(task, entry) or {"findings": task_data(task)["findings"], "trace": [entry]}

    def write(state: ResearchState) -> dict:
        payload = {"task": state["brief"]["task"], "audience": state["brief"].get("audience", "general"),
                   "findings": state["findings"]}
        task, entry = call("write_cited_answer", state["brief"]["task"], payload, state)
        result = task_data(task) or {}
        return stopped(task, entry) or {"answer": result.get("answer", task_text(task)),
                                        "sources": result.get("sources", []),
                                        "status": "completed", "trace": [entry]}

    def route(next_node: str):
        return lambda state: END if state.get("status") else next_node

    graph = StateGraph(ResearchState)
    graph.add_node("extract", extract)
    graph.add_node("research", research)
    graph.add_node("write", write)
    graph.add_edge(START, "extract")
    graph.add_conditional_edges("extract", route("research"), ["research", END])
    graph.add_conditional_edges("research", route("write"), ["write", END])
    graph.add_edge("write", END)
    return graph.compile()


def run(orchestrator, question: str, show: bool = True) -> dict:
    result = orchestrator.invoke({"question": question, "context_id": new_id(), "trace": []})
    if show:
        print("A2A calls:")
        for t in result["trace"]:
            print(f"  {t['agent']:<16} {t['skill']:<24} → {t['state']:<15} {t['seconds']:>6.1f} s")
        print(f"\nStatus: {result.get('status')}")
        if result.get("status") == "completed":
            print("\n" + result["answer"])
            print("\nSources:")
            for i, url in enumerate(result["sources"], 1):
                print(f"  [{i}] {url}")
        else:
            print(result.get("message"))
    return result
