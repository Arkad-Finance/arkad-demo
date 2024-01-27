from pathlib import Path
from langchain.sql_database import SQLDatabase
from langchain_core.language_models import BaseLanguageModel
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_experimental.autonomous_agents import AutoGPT
from langchain.tools import Tool
from langchain.agents.agent_types import AgentType
from langchain.agents import create_sql_agent
from sql_market_agent.agent.tools.prompts.sql_prompts import (
    SQL_PREFIX,
    SQL_SUFFIX,
)
from sql_market_agent.agent.tools.storage.db_fetcher import run_fetch_job
from typing import List, Dict
import logging

# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_database(
    db_connection_string: str = None,
    preinitialize_database: bool = False,
    stocks: List[Dict[str, str]] = None,
) -> SQLDatabase:
    if not db_connection_string:
        logging.info(f"DB connection string not provided, using local db on disc...")
        db_connection_string = (
            f"sqlite:///{Path(__file__).parent / 'storage/StockData.db'}"
        )

    run_fetch_job(
        stocks=stocks,
        db_connection_string=db_connection_string,
        preinitialize_database=preinitialize_database,
    )
    logging.info(f"Connecting to db for sql agent...")
    db = SQLDatabase.from_uri(db_connection_string)
    logging.info(f"Connected to db for sql agent successfully")
    return db


def get_sql_database_tool(
    llm: BaseLanguageModel,
    db_connection_string: str = None,
    preinitialize_database: bool = True,
    stocks: List[Dict[str, str]] = None,
) -> Tool:
    db = get_database(
        db_connection_string=db_connection_string,
        preinitialize_database=preinitialize_database,
        stocks=stocks,
    )
    schema_to_insert = db.get_table_info()
    sql_prefix = SQL_PREFIX.replace("{schema}", schema_to_insert)
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    db_agent = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=True,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        prefix=sql_prefix,
        suffix=SQL_SUFFIX,
    )

    sql_database_tool = Tool(
        name="sql_database_tool",
        func=db_agent.run,
        description="Useful when you need to answer questions about data in database, but only when there are no other tools to answer this question. "
        "You must use this tool only if there is no other tool for answering this specific question about data in database "
        "where there is information about US stocks symbols, sectors, OHLC data and %DailyChange data. "
        "Input should be in the form of a question containing full context. Do not use this tool if you have an answer in chat history. "
        "If there is no data available for given query - say I don't know and never hallucinate!",
    )

    return sql_database_tool
