import sqlalchemy
import os
import json
import logging
from typing import List, Dict, Optional
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sql_market_agent.agent.tools.storage.fred.fred_processor import fetch_and_insert_macro_metrics_data
from sql_market_agent.agent.tools.storage.stocks.candles.candles_processor import fetch_and_insert_stocks_data
from sql_market_agent.agent.tools.storage.stocks.sec_forms.xbrl_processor import fetch_and_insert_revenues_data

from pathlib import Path
import traceback
from datetime import datetime

# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def initialize_database(engine: sqlalchemy.engine.Engine, db_type: str):
    init_script_path = os.path.join(os.path.dirname(__file__), f"init_{db_type}_db.sql")
    with open(init_script_path, "r") as f:
        raw_sql = f.read()

    try:
        with engine.begin() as conn:  # This ensures a transaction is started
            if db_type == "sqlite":
                sql_statements = raw_sql.split(";")
                for statement in sql_statements:
                    if statement.strip():
                        conn.execute(sqlalchemy.text(statement))
            else:
                conn.execute(sqlalchemy.text(raw_sql))
        logging.info(f"Database ({db_type}) initialized.")
    except Exception as e:
        logging.error(f"An error occurred while initializing the database: {e}")


def connect_to_database(db_connection_string: str) -> sqlalchemy.engine.Engine:
    return create_engine(db_connection_string)


def read_assets_from_json(file_path: str) -> json:
    with open(file_path, "r") as file:
        return json.load(file)
    

def run_fetch_job(
    db_connection_string: str,
    preinitialize_database: bool = False,
    stocks: List[Dict[str, str]] = None,
    macro_metrics: List[Dict[str, str]] = None,
    earnings_data_path: Optional[str] = None,
    facts_data_path: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    session = None
    try:
        engine = connect_to_database(db_connection_string)
        db_type = "sqlite" if "sqlite" in db_connection_string else "postgres"
        if preinitialize_database:
            logging.info("Initializing database with StockData table...")
            initialize_database(engine, db_type)

        Session = sessionmaker(bind=engine)
        session = Session()
        logging.info("Fetching data for analysis...")

        if (
            preinitialize_database and not stocks
        ):
            stocks_json_path = Path(__file__).parent / "stocks.json"
            stocks = read_assets_from_json(stocks_json_path)
            logging.info(
                f"No stocks provided. Will use default stocks from internal stocks.json.: {stocks[0:2]}\n..."
            )

        if (
            preinitialize_database and not macro_metrics
        ):
            macro_metrics_json_path = Path(__file__).parent / "macro_metrics.json"
            macro_metrics = read_assets_from_json(macro_metrics_json_path)
            logging.info(
                f"No bonds provided. Will use default bonds from internal bonds.json.: {macro_metrics[0:2]}\n..."
            )

        if preinitialize_database:
            fetch_and_insert_stocks_data(session, stocks, start_date, end_date)
            logging.info("Data for stocks candles fetched and inserted successfully.")
            fetch_and_insert_revenues_data(session, 
                                           stocks, 
                                           earnings_data_path, 
                                           facts_data_path, 
                                           start_year=datetime.strptime(start_date, "%Y-%m-%d").date().year,
                                           end_year=datetime.strptime(end_date, "%Y-%m-%d").date().year)
            logging.info("Data for stocks revenues fetched and inserted successfully.")
            fetch_and_insert_macro_metrics_data(session, macro_metrics)
            logging.info("Data for macro metrics fetched and inserted successfully.")
        else:
            logging.info(
                "Preinitialize set to False using database as is"
            )
        
        logging.info("Data fetched and inserted successfully.")
    except (Exception, OperationalError) as error:
        logging.error(f"Database error: {error}")
        traceback.print_exc()
    finally:
        if session:
            session.close()
