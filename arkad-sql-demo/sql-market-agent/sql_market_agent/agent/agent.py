from typing import Union, List, Dict, Optional, Literal
import sys
import os

# Calculate the path to the root of the project
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

# Append the project root to the system path
sys.path.append(project_root)

from langchain.agents import AgentExecutor, AgentType
from langchain_core.language_models import BaseLanguageModel
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from langchain_core.prompts import BasePromptTemplate, PromptTemplate
from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain.agents import create_react_agent
from langchain.agents.mrkl import prompt as react_prompt
from langchain.agents.agent import (
    AgentExecutor,
    RunnableAgent,
)
from langchain_community.tools.render import format_tool_to_openai_function
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from sql_market_agent.agent.tools.tools import (
    get_tavily_search_tool,
    PythonREPLTool,
    SandboxTool,
    PythonProgrammerTool,
)
from sql_market_agent.agent.tools.prompts.prompts import (
    PREFIX,
)
from sql_market_agent.agent.tools.sql_tools import get_sql_database_tool
from sql_market_agent.agent.tools.company_overview_tools import CompanyOverviewTool
from sql_market_agent.agent.parsers.parser import parse
from dotenv import load_dotenv
import logging
from uuid import uuid4
from datetime import datetime

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

load_dotenv()

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")


def get_tools(
    sql_llm: BaseLanguageModel,
    code_llm: BaseLanguageModel,
    db_connection_string: str = None,
    preinitialize_database: bool = False,
    stocks: List[Dict[str, str]] = None,
    macro_metrics: List[Dict[str, str]] = None,
    earnings_data_path: Optional[str] = None,
    facts_data_path: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tavily_api_key: str = None,
) -> List:
    tools = []

    company_overview_tool = CompanyOverviewTool()
    tools.append(company_overview_tool)

    tavily_api_key = tavily_api_key or TAVILY_API_KEY
    if tavily_api_key:
        tavily_search_tool = get_tavily_search_tool(tavily_api_key=tavily_api_key)
        tools.append(tavily_search_tool)
    else:
        logging.info(
            msg="tavily_tool initialization failed, please provide Tavily API key"
        )
    sql_database_tool = get_sql_database_tool(
        llm=sql_llm,
        db_connection_string=db_connection_string,
        preinitialize_database=preinitialize_database,
        stocks=stocks,
        macro_metrics=macro_metrics,
        earnings_data_path=earnings_data_path,
        facts_data_path=facts_data_path,
        start_date=start_date,
        end_date=end_date,
    )
    tools.append(sql_database_tool)

    python_code_checker_tool = PythonProgrammerTool(llm=code_llm)
    tools.append(python_code_checker_tool)

    repl_tool = SandboxTool()
    # repl_tool = PythonREPLTool()
    tools.append(repl_tool)

    return tools

def create_dir(dir_path: str):
    if not os.path.exists(dir_path):
        # Create the directory
        os.makedirs(dir_path)
        print(f"Directory '{dir_path}' created")
    else:
        print(f"Directory '{dir_path}' already exists")


def create_sql_market_agent(
    llm: BaseLanguageModel,
    sql_llm: BaseLanguageModel,
    code_llm: BaseLanguageModel,
    agent_type: Optional[Union[AgentType, Literal["openai-tools"]]] = None,
    prompt: Optional[BasePromptTemplate] = None,
    prefix: Optional[str] = None,
    format_instructions: Optional[str] = None,
    db_connection_string: Optional[str] = None,
    preinitialize_database: Optional[bool] = False,
    stocks: Union[List[str], List[Dict[str, str]]] = None,
    macro_metrics: List[Dict[str, str]] = None,
    earnings_data_path: Optional[str] = None,
    facts_data_path: Optional[str] = None,
    start_date: Optional[str] = "2020-01-01",
    end_date: Optional[str] = datetime.now().strftime('%Y-%m-%d'),
    tavily_api_key: str = None,
) -> AgentExecutor:
    # Not proceeding if db_connection_string is None and preinitialize_database is False
    if db_connection_string is None and not preinitialize_database:
        raise ValueError(
            "A database connection string must be provided or the preinitialize_database must be set to True."
        )

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

    # Create directories for agent artifacts
    artifacts_directories = ["./charts", earnings_data_path, facts_data_path]
    for dir in artifacts_directories:
        if dir:
            create_dir(dir)

    agent_type = agent_type or AgentType.ZERO_SHOT_REACT_DESCRIPTION

    tools = get_tools(
        sql_llm=sql_llm,
        code_llm=code_llm,
        db_connection_string=db_connection_string,
        preinitialize_database=preinitialize_database,
        stocks=stocks,
        macro_metrics=macro_metrics,
        earnings_data_path=earnings_data_path,
        facts_data_path=facts_data_path,
        start_date=start_date,
        end_date=end_date,
        tavily_api_key=tavily_api_key,
    )

    if prompt is None:
        prefix = prefix or PREFIX

    if agent_type == AgentType.ZERO_SHOT_REACT_DESCRIPTION:
        if prompt is None:
            format_instructions = (
                format_instructions or react_prompt.FORMAT_INSTRUCTIONS
            )
            template = "\n\n".join(
                [
                    react_prompt.PREFIX,
                    "{tools}",
                    format_instructions,
                    react_prompt.SUFFIX,
                ]
            )
            prompt = PromptTemplate.from_template(template)
        agent = RunnableAgent(
            runnable=create_react_agent(llm, tools, prompt),
            input_keys_arg=["input"],
            return_keys_arg=["output"],
        )

    elif agent_type == AgentType.OPENAI_FUNCTIONS:
        if prompt is None:
            messages = [
                SystemMessage(content=prefix),
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template("{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
            prompt = ChatPromptTemplate.from_messages(messages)
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
            # | parse
        )

    else:
        raise ValueError(
            f"Agent type {agent_type} not supported at the moment. Must be one of "
            "'openai-functions' or 'zero-shot-react-description'."
        )
    
    agent_executor = AgentExecutor(agent=agent, 
                                   tools=tools, 
                                   verbose=True, 
                                   handle_parsing_errors=True, 
                                   return_intermediate_steps=True)
    
    return agent_executor
