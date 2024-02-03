from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool, Tool
from typing import Type
from langchain.chains import LLMMathChain
from langchain_openai.chat_models import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
from langchain_experimental.utilities import PythonREPL
from dotenv import load_dotenv
import logging

# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()


# Calculator tool
class CalculatorInput(BaseModel):
    query: str = Field(
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


# PythonREPL tool. Warning: This executes code locally, which can be unsafe when not sandboxed
class PythonREPLInput(BaseModel):
    code: str = Field(
        description="The python code to execute to do code calculations or generate chart."
    )


class PythonREPLTool(BaseTool):
    name = "PythonREPLTool"
    description = """Use this to execute python code for complex calculations or for chart plotting. 
    If you want to see the output of a value, 
    you should print it out with `print(...)`. This is visible to the user."""
    args_schema: Type[BaseModel] = PythonREPLInput
    repl = PythonREPL()

    def _run(self, code: str) -> str:
        try:
            result = self.repl.run(code)
        except BaseException as e:
            return f"Failed to execute. Error: {repr(e)}"
        return f"Succesfully executed:\n```python\n{code}\n```\nStdout: {result}"


# Search tool
def get_tavily_search_tool(tavily_api_key: str = None) -> Tool:
    description = """A search engine optimized for comprehensive, accurate, \
        and trusted results. Useful for when you need to answer questions \
        about current events or about recent information. \
        Input should be a search query. \
        If the user is asking about something that you don't know about, \
        you should probably use this tool to see if that can provide any information."""
    search = TavilySearchAPIWrapper(tavily_api_key=tavily_api_key)
    tavily_tool = TavilySearchResults(api_wrapper=search, description=description)

    return tavily_tool
