from crewai import Crew, Agent, Task, LLM
from langchain_community.tools.tavily_search import TavilySearchResults
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv

load_dotenv()

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY") 
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT") 
AZURE_OPENAI_API_VERSION = "2024-12-01-preview" 
AZURE_OPENAI_DEPLOYMENT = "gpt-5-mini" 

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY") 

class ToolInput(BaseModel):
    question: str = Field(description="search query")


class SearchTool(BaseTool):
    name: str = "Search tool"
    description: str = "use this tool to find current information required for query"
    args_schema: type = ToolInput

    def _run(self, question: str):
        """use this tool to find current information required for query"""
        web_search = TavilySearchResults(
            tavily_api_key=TAVILY_API_KEY
        )
        result = web_search.invoke({"query": question})
        return str(result)

def create_crewai_agent(task_description: str):
    llm = LLM( 
        model="azure/gpt-5-mini", 
        api_key=AZURE_OPENAI_API_KEY, 
        base_url=AZURE_OPENAI_ENDPOINT, 
        api_version=AZURE_OPENAI_API_VERSION, 
        is_litellm=True,
        max_tokens=3000 
    )

    researcher = Agent(
        role="Researcher",
        goal="Search the web and gather information",
        backstory="Expert in web research using advanced techniques",
        tools=[SearchTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

    task = Task(
        description=f"Research this briefly and return 5 bullet points only: {task_description}",
        expected_output="5 short bullet points with the most relevant findings",
        agent=researcher
    )

    crew = Crew(
        agents=[researcher],
        tasks=[task],
        verbose=True,
    )

    return crew