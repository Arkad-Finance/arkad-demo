from pathlib import Path
import pandas as pd
from langchain_core.pydantic_v1 import Field, BaseModel, root_validator
from langchain_core.prompts import PromptTemplate
from langchain.sql_database import SQLDatabase
from langchain_core.language_models import BaseLanguageModel
from langchain.chains.llm import LLMChain
from langchain_community.agent_toolkits.base import BaseToolkit
from langchain.tools import Tool, BaseTool
from langchain.agents.agent_types import AgentType
from langchain.agents import create_sql_agent
from langchain_core.language_models import BaseLanguageModel
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from sql_market_agent.agent.tools.prompts.sql_prompts import (
    SQL_PREFIX,
    SQL_SUFFIX,
    QUERY_CHECKER,
)
from sql_market_agent.agent.tools.storage.db_fetcher import run_fetch_job
from typing import List, Dict, Optional, Any, Type
import logging
import json
from datetime import datetime

# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def read_assets_from_json(file_path: str) -> json:
    with open(file_path, "r") as file:
        return json.load(file)


MACRO_METRICS_DESCRIPTION = read_assets_from_json(
    file_path=Path(__file__).parent / "storage/macro_metrics.json"
)
DB_TABLES_DESCRIPTION = {
    "stockdata": {
        "description": "sector, date, open, high, low, close, volume, dailychangepercent data about stocks"
    },
    "stockfinancialdata": {
        "description": "fundamental data about both quarterly and yearly earnings per year ('FY') "
        "and per each quarter ('Q1', 'Q2', 'Q3', 'Q4') in each year.",
        "data_categories_description": "available columns: symbol; sector; year; "
        "reporttype - currently only 'Revenue'; period - one of 'Q1', 'Q2', 'Q3', 'Q4', 'FY'; "
        "amount in USD, qoq - percent change relative to previous quarter for quarterly reports; "
        "yoy - percent change relative to same quarter of previous year for quarterly reports and "
        "percent change relative to previous year for full year reports.",
    },
    "macrometricdata": {
        "description": "macrometric, description, date, macrometricvalue, periodicchangepercent data about macrometrics including "
        "data about treasury bonds yield.",
        "data_categories_description": MACRO_METRICS_DESCRIPTION,
    },
}

TEMP_CSV_PATH = "./artifacts/temp.csv"


def dump_string_to_dataframe(data_string):
    data_string = data_string.replace("'", '"')
    data_list = json.loads(data_string)
    df = pd.DataFrame(data_list)
    logging.info(f"Saving intermediate data fetching result to {TEMP_CSV_PATH}...")
    df.to_csv(TEMP_CSV_PATH)
    logging.info(f"Saved to {TEMP_CSV_PATH}...")
    return df.head()


class BaseSQLDatabaseTool(BaseModel):
    """Base tool for interacting with a SQL database."""

    db: SQLDatabase = Field(exclude=True)

    class Config(BaseTool.Config):
        pass


class _QuerySQLDataBaseToolInput(BaseModel):
    query: str = Field(..., description="A detailed and correct SQL query.")


class QuerySQLDataBaseTool(BaseSQLDatabaseTool, BaseTool):
    """Tool for querying a SQL database"""

    name: str = "sql_db_query"
    description: str = """
    Execute a SQL query against the database and get back the result, save it to .csv file and return 
    path to that file with df.head(). 
    If the query is not correct, an error message will be returned.
    If an error is returned, rewrite the query, check the query, and try again.
    """

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute the query, return the results or an error message."""
        query_result = self.db.run_no_throw(query, include_columns=True)
        if "Error" in query_result:
            return query_result
        if not query_result or "[]" in query_result:
            return {
                "error": "empty result, please double check database schema if you are doing things correctly"
            }
        data_head = dump_string_to_dataframe(query_result)
        return {"data_path": TEMP_CSV_PATH, "data_head": data_head}


class _InfoSQLDatabaseToolInput(BaseModel):
    table_names: str = Field(
        ...,
        description=(
            "A comma-separated list of the table names for which to return the schema. "
            "Example input: 'table1, table2, table3'"
        ),
    )


class InfoSQLDatabaseTool(BaseSQLDatabaseTool, BaseTool):
    """Tool for getting metadata about a SQL database."""

    name: str = "sql_db_schema"
    description: str = "Get the schema and sample rows for the specified SQL tables."
    args_schema: Type[BaseModel] = _InfoSQLDatabaseToolInput

    def _run(
        self,
        table_names: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get the schema for tables in a comma-separated list."""
        return self.db.get_table_info_no_throw(
            [t.strip() for t in table_names.split(",")]
        )


class ListSQLDatabaseTool(BaseSQLDatabaseTool, BaseTool):
    """Tool for getting tables names."""

    name: str = "sql_db_list_tables"
    description: str = (
        "Input is an empty string, output is a comma separated list of tables in the database."
    )

    def _run(
        self,
        tool_input: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get the schema for a specific table."""
        return ", ".join(self.db.get_usable_table_names())


class QuerySQLCheckerTool(BaseTool):
    """Use an LLM to check if a query is correct.
    Adapted from https://www.patterns.app/blog/2023/01/18/crunchbot-sql-analyst-gpt/"""

    template: str = QUERY_CHECKER
    db_dialect: str = None
    llm: BaseLanguageModel = None
    llm_chain: Any = Field(init=False)
    name: str = "sql_db_query_checker"
    description: str = """
    Use this tool to double check if your query is correct before executing it.
    Always use this tool before executing a query with sql_db_query or sql_intermediate_db_query!
    """

    def __init__(self, db_dialect: SQLDatabase, llm: BaseLanguageModel):
        super().__init__()
        self.db_dialect = db_dialect
        self.llm = llm
        self.llm_chain = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                template=self.template,
                input_variables=["dialect", "query", "current_date"],
            ),
        )

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the LLM to check the query."""
        return self.llm_chain.predict(
            query=query,
            dialect=self.db_dialect,
            current_date=datetime.now().strftime("%Y-%m-%d"),
            callbacks=run_manager.get_child() if run_manager else None,
        )

    async def _arun(
        self,
        query: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        return await self.llm_chain.apredict(
            query=query,
            dialect=self.db.dialect,
            current_date=datetime.now().strftime("%Y-%m-%d"),
            callbacks=run_manager.get_child() if run_manager else None,
        )


class SQLDatabaseToolkit(BaseToolkit):
    """Toolkit for interacting with SQL databases."""

    db: SQLDatabase = Field(exclude=True)
    llm: BaseLanguageModel = Field(exclude=True)

    @property
    def dialect(self) -> str:
        """Return string representation of SQL dialect to use."""
        return self.db.dialect

    class Config:
        """Configuration for this pydantic object."""

        arbitrary_types_allowed = True

    def get_tools(self) -> List[BaseTool]:
        """Get the tools in the toolkit."""
        list_sql_database_tool = ListSQLDatabaseTool(db=self.db)
        info_sql_database_tool_description = (
            "Input to this tool is a comma-separated list of tables, output is the "
            "schema and sample rows for those tables. "
            "Be sure that the tables actually exist by calling "
            f"{list_sql_database_tool.name} first! "
            "Example Input: table1, table2, table3"
        )
        info_sql_database_tool = InfoSQLDatabaseTool(
            db=self.db, description=info_sql_database_tool_description
        )
        query_sql_database_tool_description = (
            "Input to this tool is a detailed and correct SQL query, output is a "
            "path to .csv file on disc where result is saved along with df.head() "
            "If the query is not correct, an error message "
            "will be returned. If an error is returned, rewrite the query, check the "
            "query, and try again. If you encounter an issue with Unknown column "
            f"'xxxx' in 'field list', use {info_sql_database_tool.name} "
            "to query the correct table fields."
        )
        query_sql_database_tool = QuerySQLDataBaseTool(
            db=self.db, description=query_sql_database_tool_description
        )
        query_sql_checker_tool = QuerySQLCheckerTool(
            db_dialect=self.db.dialect, llm=self.llm
        )
        return [
            query_sql_database_tool,
            info_sql_database_tool,
            list_sql_database_tool,
            query_sql_checker_tool,
        ]

    def get_context(self) -> dict:
        """Return db context that you may want in agent prompt."""
        return self.db.get_context()


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
        end_date=end_date,
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
        end_date=end_date,
    )
    schema_to_insert = db.get_table_info()
    sql_prefix = SQL_PREFIX.replace("{schema}", schema_to_insert).replace(
        "{additional_description}",
        json.dumps(DB_TABLES_DESCRIPTION).replace("{", "{{").replace("}", "}}"),
    )
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
