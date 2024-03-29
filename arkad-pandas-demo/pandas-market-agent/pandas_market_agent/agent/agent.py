from typing import Union, List, Dict
import sys
import os


# Calculate the path to the root of the project
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

# Append the project root to the system path
sys.path.append(project_root)

from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain_core.language_models import BaseLanguageModel
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.tools.render import format_tool_to_openai_function
from pandas_market_agent.agent.tools.tools import get_tavily_search_tool, CalculatorTool, PythonREPLTool
# from pandas_market_agent.agent.tools.datetime_tools import DateTool
from pandas_market_agent.agent.tools.pandas_tools import PandasTool
from pandas_market_agent.agent.tools.company_overview_tools import CompanyOverviewTool
from dotenv import load_dotenv
import logging

# Setup basic logging
# Configure logging to file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

load_dotenv()

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")


def get_tools(
    llm: BaseLanguageModel,
    stocks: List[Dict[str, str]] = None,
    tavily_api_key: str = None,
) -> List:
    # date_tool = DateTool()
    calculator_tool = CalculatorTool()
    company_overview_tool = CompanyOverviewTool()
    repl_tool = PythonREPLTool()

    tools = [calculator_tool, repl_tool, company_overview_tool]

    tavily_api_key = tavily_api_key or TAVILY_API_KEY
    if tavily_api_key:
        tavily_search_tool = get_tavily_search_tool(tavily_api_key=tavily_api_key)
        tools.append(tavily_search_tool)
    else:
        logging.info(
            msg="tavily_tool initialization failed, please provide Tavily API key"
        )
    pandas_tool = PandasTool(llm=llm, stocks=stocks)

    tools.append(pandas_tool)

    return tools


def create_pandas_market_agent(
    llm: BaseLanguageModel,
    stocks: Union[List[str], List[Dict[str, str]]] = None,
    tavily_api_key: str = None,
) -> AgentExecutor:
    # Check if stocks is a list of strings
    if stocks and all(isinstance(stock, str) for stock in stocks):
        stocks = [{"ticker": stock, "sector": ""} for stock in stocks]

    # Check if stocks is a list of dictionaries with the keys 'ticker' and 'sector'
    elif stocks and all(
        isinstance(stock, dict) and "ticker" in stock and "sector" in stock
        for stock in stocks
    ):
        pass  # stocks is already in the desired format

    else:
        # Handle the case where stocks is not in one of the expected formats
        logging.warn(
            "Invalid format for stocks. Expected a list of strings or a list of dictionaries with 'ticker' and 'sector' keys. "
            "Will use default stocks from internal stocks.json."
        )

    tools = get_tools(
        llm=llm,
        stocks=stocks,
        tavily_api_key=tavily_api_key,
    )
    assistant_system_message = """You are a helpful assistant. \
        Use tools (only if necessary) to best answer the users questions."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", assistant_system_message),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )
    llm_with_tools = llm.bind(
        functions=[format_tool_to_openai_function(t) for t in tools]
    )
    agent = (
        {
            "input": lambda x: x["input"],
            "chat_history": lambda x: x["chat_history"],
            "agent_scratchpad": lambda x: format_to_openai_function_messages(
                x["intermediate_steps"]
            ),
        }
        | prompt
        | llm_with_tools
        | OpenAIFunctionsAgentOutputParser()
    )
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    return agent_executor
