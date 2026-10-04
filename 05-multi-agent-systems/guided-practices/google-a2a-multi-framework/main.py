from typing import TypedDict

from langgraph.graph import StateGraph, END
from agents.langchain_agent import create_langchain_agent
from agents.crewai_agent import create_crewai_agent
from agents.custom_openai_agent import generate_response


### Define State
class A2AState(TypedDict, total=False):
    input: str
    task: str
    web_results: str
    final_response: str


### Define Nodes
def langchain_node(state):
    print("state is: ", state)
    return {"task": state["input"]}


def crewai_node(state):
    print(" state task is: ", state["task"])
    crew = create_crewai_agent(task_description=state["task"])
    result = crew.kickoff()
    return {"web_results": str(result)}


def openai_response_node(state):
    prompt = f"Based on the web results: {state['web_results']}, respond to the task: {state['task']}"
    response = generate_response(prompt)
    return {"final_response": response}


### Build Graph
builder = StateGraph(A2AState)
builder.add_node("LangChainAgent", langchain_node)
builder.add_node("CrewAIAgent", crewai_node)
builder.add_node("OpenAIAgent", openai_response_node)

# Edges
builder.set_entry_point("LangChainAgent")
builder.add_edge("LangChainAgent", "CrewAIAgent")
builder.add_edge("CrewAIAgent", "OpenAIAgent")
builder.add_edge("OpenAIAgent", END)

graph = builder.compile()

### Execute
if __name__ == "__main__":
    input_text = "Can you summarize the latest trends in GenAI for enterprise?"
    output = graph.invoke({"input": input_text})
    print("Final Output:\n", output["final_response"])