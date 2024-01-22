from pathlib import Path
import os
import openai
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool
from typing import Type
from langchain.chains import LLMMathChain
from langchain_openai.chat_models import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")


# Calculator tool
class CalculatorInput(BaseModel):
    a: str = Field(
        description="Some math question in natural language which need computation."
    )


class CalculatorTool(BaseTool):
    name = "calculator"
    description = "Useful for when you need to answer questions about math."
    args_schema: Type[BaseModel] = CalculatorInput

    def _run(self, query: str) -> str:
        llm = ChatOpenAI(temperature=0, model="gpt-4", streaming=True)
        llm_math_chain = LLMMathChain.from_llm(llm)
        return llm_math_chain.run(query)


# Search tool
class SearchInput(BaseModel):
    query: str = Field(description="Should be a search query.")


class TavilySearchTool(BaseTool):
    name = "search"
    description = """A search engine optimized for comprehensive, accurate, \
        and trusted results. Useful for when you need to answer questions \
        about current events or about recent information. \
        Input should be a search query. \
        If the user is asking about something that you don't know about, \
        you should probably use this tool to see if that can provide any information."""
    args_schema: Type[BaseModel] = SearchInput
    search = TavilySearchAPIWrapper(tavily_api_key=TAVILY_API_KEY)
    tavily_tool = TavilySearchResults(api_wrapper=search, description=description)

    def _run(self, query: str) -> str:
        return self.tavily_tool.run(query)
