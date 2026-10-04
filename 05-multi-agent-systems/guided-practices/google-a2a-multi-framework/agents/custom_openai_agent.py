import os
from dotenv import load_dotenv

load_dotenv()
from crewai import LLM

llm = LLM(
    model="azure/gpt-5-mini",
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-12-01-preview",
    is_litellm=True,
)

def generate_response(prompt: str) -> str:
    response = llm.call(prompt)
    return str(response)