from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import AzureChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()


@tool
def extract_task_from_input(input_text: str) -> str:
    """Extract the core task from user input."""
    return f"Extracted task from input: {input_text.strip()}"


def create_langchain_agent():
    llm = AzureChatOpenAI(
        azure_deployment="gpt-5-mini",  
        api_version="2024-12-01-preview",
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    )

    tools = [extract_task_from_input]

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt="You are a helpful assistant."
    )
    return agent