import yfinance as yf
import pandas as pd
import sqlalchemy
import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import text, insert, select
from sqlalchemy.dialects.postgresql import insert as insert_postgres
from pathlib import Path
import traceback

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


def fetch_stock_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    stock = yf.Ticker(symbol)
    return stock.history(start=start_date, end=end_date)


def calculate_daily_change(current_close: float, previous_close: float) -> float:
    return (
        (current_close - previous_close) / previous_close * 100
        if previous_close is not None
        else None
    )


def get_last_date_for_stock(session: sqlalchemy.orm.Session, symbol: str) -> str:
    result = session.execute(
        text("SELECT MAX(Date) FROM StockData WHERE Symbol = :symbol"),
        {"symbol": symbol},
    ).fetchone()
    last_date = None
    if result:
        last_date = (
            datetime.strptime(result[0], "%Y-%m-%d").date()
            if isinstance(result[0], str)
            else result[0]
        )

    return last_date


def get_last_close_for_stock(
    session: sqlalchemy.orm.Session, stock_table: sqlalchemy.Table, symbol: str
) -> float:
    last_close_query = (
        select(stock_table.c.close)
        .where(stock_table.c.symbol == symbol)
        .order_by(stock_table.c.date.desc())
        .limit(1)
    )
    result = session.execute(last_close_query).fetchone()
    return result[0] if result else None


def fetch_and_insert_data(
    session: sqlalchemy.orm.Session, stocks: List[Dict[str, str]]
):
    stock_table = sqlalchemy.Table(
        "stockdata", sqlalchemy.MetaData(), autoload_with=session.bind
    )

    for stock in stocks:
        symbol = stock["ticker"]
        sector = stock["sector"]
        last_date = get_last_date_for_stock(session, symbol)
        start_date = (
            (last_date + timedelta(days=1))
            if last_date
            else (datetime.now() - timedelta(days=30)).date()
        )
        end_date = datetime.now().date()
        if start_date < end_date:
            stock_data = fetch_stock_data(
                symbol, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
            )

            prev_close = get_last_close_for_stock(session, stock_table, symbol)
            data_to_insert = []
            for index, row in stock_data.iterrows():
                daily_change = calculate_daily_change(row["Close"], prev_close)
                prev_close = row["Close"]
                if daily_change is not None:
                    data_to_insert.append(
                        {
                            "symbol": symbol,
                            "sector": sector,
                            "date": index.strftime("%Y-%m-%d"),
                            "open": row["Open"],
                            "high": row["High"],
                            "low": row["Low"],
                            "close": row["Close"],
                            "volume": row["Volume"],
                            "dailychangepercent": daily_change,
                        }
                    )

            if session.bind.dialect.name == "postgresql":
                statement = (
                    insert_postgres(stock_table)
                    .values(data_to_insert)
                    .on_conflict_do_nothing()
                )
            elif session.bind.dialect.name == "sqlite":
                statement = (
                    insert(stock_table).values(data_to_insert).prefix_with("OR IGNORE")
                )

            session.execute(statement)
            session.commit()


def read_stocks_from_json(file_path: str) -> json:
    with open(file_path, "r") as file:
        return json.load(file)


def run_fetch_job(
    db_connection_string: str,
    preinitialize_database: bool = False,
    stocks: List[Dict[str, str]] = None,
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
        ):  # If preinitializing database - it must have at least some data.
            # If no stocks passed - read from json
            stocks_json_path = Path(__file__).parent / "stocks.json"
            stocks = read_stocks_from_json(stocks_json_path)
            logging.info(
                f"No stocks provided. Will use default stocks from internal stocks.json.: {stocks[0:2]}\n..."
            )

        if stocks:
            fetch_and_insert_data(session, stocks)
            logging.info("Data fetched and inserted successfully.")
        else:
            logging.info(
                "Preinitialize set to False and no stocks provided, using database as is"
            )
    except (Exception, OperationalError) as error:
        logging.error(f"Database error: {error}")
        traceback.print_exc()
    finally:
        if session:
            session.close()
