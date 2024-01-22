from typing import Union, List, Dict
import sys
import os


# Calculate the path to the root of the project
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

# Append the project root to the system path
sys.path.append(project_root)

import openai
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain_openai.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.messages import AIMessage, HumanMessage
from langchain_community.tools.render import format_tool_to_openai_function
from sql_market_agent.agent.tools.tools import TavilySearchTool, CalculatorTool
from sql_market_agent.agent.tools.datetime_tools import DateTool
from sql_market_agent.agent.tools.sql_tools import get_sql_database_tool
from sql_market_agent.agent.tools.alpha_vantage_tools import CompanyOverviewTool
from dotenv import load_dotenv
import logging

# Setup basic logging
# Configure logging to file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY


def get_tools(stocks: List = None) -> List:
    date_tool = DateTool()
    calculator_tool = CalculatorTool()
    company_overview_tool = CompanyOverviewTool()
    tavily_search_tool = TavilySearchTool()
    sql_database_tool = get_sql_database_tool(stocks=stocks)

    return [
        date_tool,
        calculator_tool,
        company_overview_tool,
        tavily_search_tool,
        sql_database_tool,
    ]


def create_openai_sql_market_agent(
    stocks: Union[List[str], List[Dict[str, str]]] = None
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
        logging.error(
            "Invalid format for stocks. Expected a list of strings or a list of dictionaries with 'ticker' and 'sector' keys."
        )
        return None  # Or raise an exception, or handle this case as you see fit

    logging.info(f"Stocks: {stocks}")
    logging.info(msg=f"Stocks: {stocks}")
    tools = get_tools(stocks=stocks)
    llm = ChatOpenAI(temperature=0, model="gpt-4", streaming=True)
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
