from pathlib import Path
import os
from langchain.sql_database import SQLDatabase
from langchain_openai.chat_models import ChatOpenAI
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
from dotenv import load_dotenv
from sql_market_agent.agent.tools.storage.db_fetcher import (
    run_fetch_job as run_db_fetch_job,
)
from sql_market_agent.agent.tools.storage.disc_fetcher import (
    run_fetch_job as run_disc_fetch_job,
)
from typing import List
import logging

# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB")
DB_USER = os.environ.get("POSTGRES_USER")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD")


def env_vars_set() -> bool:
    """Check if all required environment variables are set."""
    required_vars = [DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD]
    return all(required_vars)


def init_db(stocks: List = None) -> SQLDatabase:
    if env_vars_set():
        run_db_fetch_job(stocks=stocks)
        return SQLDatabase.from_uri(
            f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )
    run_disc_fetch_job(stocks=stocks)
    db_path = Path(__file__).parent / "storage/StockData.db"
    return SQLDatabase.from_uri(db_path)


def get_sql_database_tool(stocks: List = None) -> Tool:
    llm = ChatOpenAI(temperature=0, model="gpt-4", streaming=True)
    db = init_db(stocks=stocks)
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
        "Input should be in the form of a question containing full context. Do not use this tool if you have an answer in chat history.",
    )

    return sql_database_tool
