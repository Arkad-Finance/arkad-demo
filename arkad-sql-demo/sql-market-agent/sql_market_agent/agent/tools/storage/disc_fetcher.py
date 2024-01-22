import sqlite3
import yfinance as yf
import pandas as pd
import os
import json
import logging
from datetime import datetime, timedelta
import traceback
import time
from pathlib import Path
from typing import List

# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def initialize_database(db_path: str, init_script_path: str):
    with sqlite3.connect(db_path) as conn:
        with open(init_script_path, "r") as f:
            conn.executescript(f.read())
    logging.info("Database initialized.")


def connect_to_database(db_path: str) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def fetch_stock_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    stock = yf.Ticker(symbol)
    df = stock.history(start=start_date, end=end_date)
    return df


def calculate_daily_change(current_close: float, previous_close: float) -> float:
    if previous_close is not None:
        return (current_close - previous_close) / previous_close * 100
    return None


def get_last_date_for_stock(cursor: sqlite3.Cursor, symbol: str) -> str:
    cursor.execute("SELECT MAX(Date) FROM StockData WHERE Symbol = ?", (symbol,))
    last_date = cursor.fetchone()[0]
    return last_date


def read_stocks_from_json(file_path: str) -> json:
    with open(file_path, "r") as file:
        return json.load(file)


def fetch_and_insert_data(cursor: sqlite3.Cursor, stocks):
    insert_query = (
        "INSERT INTO StockData (Symbol, Sector, Date, Open, High, Low, "
        "Close, Volume, DailyChangePercent) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    for stock in stocks:
        symbol = stock["ticker"]
        sector = stock["sector"]

        last_date = get_last_date_for_stock(cursor, symbol)
        start_date = (
            (last_date + timedelta(days=1))
            if last_date
            else datetime.now() - timedelta(days=30)
        ).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        if start_date != end_date:
            stock_data = fetch_stock_data(symbol, start_date, end_date)

            data_to_insert = []
            cursor.execute(
                "SELECT Close FROM StockData WHERE Symbol = ? ORDER BY Date DESC LIMIT 1",
                (symbol,),
            )
            result = cursor.fetchone()
            prev_close = result[0] if result else None

            for index, row in stock_data.iterrows():
                date = index.strftime("%Y-%m-%d")
                open_price, high, low, close, volume = (
                    row["Open"],
                    row["High"],
                    row["Low"],
                    row["Close"],
                    row["Volume"],
                )
                daily_change_percent = calculate_daily_change(close, prev_close)
                if daily_change_percent is not None:
                    data_to_insert.append(
                        (
                            symbol,
                            sector,
                            date,
                            open_price,
                            high,
                            low,
                            close,
                            volume,
                            daily_change_percent,
                        )
                    )

                prev_close = close

            cursor.executemany(insert_query, data_to_insert)


def run_fetch_job(stocks: List = None):
    try:
        db_path = Path(__file__).parent / "StockData.db"
        init_script_path = Path(__file__).parent / "init_demo_db.sql"
        logging.info("Initializing database...")
        initialize_database(db_path, init_script_path)

        logging.info("Establishing database connection...")
        conn = connect_to_database(db_path)
        cursor = conn.cursor()

        logging.info("Fetching data for analysis...")
        logging.info(f"Stocks: {stocks}")
        if not stocks:
            # If no stocks passed - read from json
            stocks_json_path = Path(__file__).parent / "stocks.json"
            stocks = read_stocks_from_json(stocks_json_path)

        fetch_and_insert_data(cursor, stocks)
        logging.info("Data fetched and inserted successfully...")
        conn.commit()
    except Exception as error:
        logging.error(f"Database error: {error}")
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")
