from pathlib import Path
from langchain.sql_database import SQLDatabase
from langchain_core.language_models import BaseLanguageModel
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain.tools import Tool
from langchain.agents.agent_types import AgentType
from langchain.agents import create_sql_agent
from sql_market_agent.agent.tools.prompts.sql_prompts import (
    SQL_PREFIX,
    SQL_SUFFIX,
)
from sql_market_agent.agent.tools.storage.db_fetcher import run_fetch_job
from typing import List, Dict, Optional
import logging
import json

# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def read_assets_from_json(file_path: str) -> json:
    with open(file_path, "r") as file:
        return json.load(file)


MACRO_METRICS_DESCRIPTION = read_assets_from_json(file_path=Path(__file__).parent / "storage/macro_metrics.json")
DB_TABLES_DESCRIPTION = {
    "stockdata": {"description": "sector, date, open, high, low, close, volume, dailychangepercent data about stocks"},
    "stockfinancialdata": {"description": "fundamental data about both quarterly and yearly earnings per year ('FY') "
                           "and per each quarter ('Q1', 'Q2', 'Q3', 'Q4') in each year.",
                           "data_categories_description": "available columns: symbol; sector; year; "
                           "reporttype - currently only 'Revenue'; period - one of 'Q1', 'Q2', 'Q3', 'Q4', 'FY'; "
                           "amount in USD, qoq - percent change relative to previous quarter for quarterly reports; "
                           "yoy - percent change relative to same quarter of previous year for quarterly reports and "
                           "percent change relative to previous year for full year reports."},
    "macrometricdata": {"description": "macrometric, description, date, macrometricvalue, periodicchangepercent data about macrometrics including "
                        "data about treasury bonds yield.",
                        "data_categories_description": MACRO_METRICS_DESCRIPTION},
}


def get_database(
    db_connection_string: str = None,
    preinitialize_database: bool = False,
    stocks: List[Dict[str, str]] = None,
    macro_metrics: List[Dict[str, str]] = None,
    earnings_data_path: Optional[str] = None,
    facts_data_path: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> SQLDatabase:
    if not db_connection_string:
        logging.info(f"DB connection string not provided, using local db on disc...")
        db_connection_string = (
            f"sqlite:///{Path(__file__).parent / 'storage/StockData.db'}"
        )

    run_fetch_job(
        stocks=stocks,
        macro_metrics=macro_metrics,
        db_connection_string=db_connection_string,
        preinitialize_database=preinitialize_database,
        earnings_data_path=earnings_data_path,
        facts_data_path=facts_data_path,
        start_date=start_date,
        end_date=end_date
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
    macro_metrics: List[Dict[str, str]] = None,
    earnings_data_path: Optional[str] = None,
    facts_data_path: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Tool:
    db = get_database(
        db_connection_string=db_connection_string,
        preinitialize_database=preinitialize_database,
        stocks=stocks,
        macro_metrics=macro_metrics,
        earnings_data_path=earnings_data_path,
        facts_data_path=facts_data_path,
        start_date=start_date,
        end_date=end_date
    )
    schema_to_insert = db.get_table_info()
    sql_prefix = SQL_PREFIX.replace("{schema}", schema_to_insert) \
        .replace("{additional_description}", json.dumps(DB_TABLES_DESCRIPTION)
                 .replace("{", "{{").replace("}", "}}"))
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    db_agent = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=True,
        agent_type=AgentType.OPENAI_FUNCTIONS,
        prefix=sql_prefix,
        suffix=SQL_SUFFIX,
    )

    sql_database_tool = Tool(
        name="sql_database_tool",
        func=db_agent.run,
        description="Useful when you need to answer questions about data in database, but only when there are no other tools to answer this question. "
        "You must use this tool only if there is no other tool for answering this specific question about data in database "
        "where there is information about US stocks, bonds and macro metrics data. If you are not sure what column to use - try to use description column if available "
        "to understand what to select and how to filter. "
        "Input should be in the form of a question containing full context. Do not use this tool if you have an answer in chat history. "
        "If there is no data available for given query - say I don't know and never hallucinate!",
    )

    return sql_database_tool
