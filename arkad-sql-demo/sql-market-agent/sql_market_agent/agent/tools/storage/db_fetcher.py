# fetch_data.py
import yfinance as yf
import pandas as pd
import psycopg2
import os
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import traceback
import time
from typing import Union, List, Dict


# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

# Database configuration
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB")
DB_USER = os.environ.get("POSTGRES_USER")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD")


def connect_to_database(
    attempts: int = 5, delay: int = 10
) -> psycopg2.extensions.connection:
    for attempt in range(attempts):
        try:
            conn = psycopg2.connect(
                dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST
            )
            logging.info("Database connection established.")
            return conn
        except psycopg2.OperationalError as e:
            logging.warning(
                f"Attempt {attempt + 1} failed to connect to the database: {e}"
            )
            if attempt < attempts - 1:
                logging.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logging.error("All attempts to connect to the database have failed.")
                raise


# Function to fetch data from Yahoo Finance
def fetch_stock_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    stock = yf.Ticker(symbol)
    df = stock.history(start=start_date, end=end_date)
    return df


# Function to calculate daily change percentage
def calculate_daily_change(current_close: float, previous_close: float) -> float:
    if previous_close is not None:
        return (current_close - previous_close) / previous_close * 100
    return None


# Function to get the last date for a specific stock
def get_last_date_for_stock(cursor: psycopg2.extensions.cursor, symbol: str) -> str:
    cursor.execute("SELECT MAX(Date) FROM StockData WHERE Symbol = %s", (symbol,))
    last_date = cursor.fetchone()[0]
    return last_date


# Function to read stocks from a JSON file
def read_stocks_from_json(file_path: str) -> Union[List, Dict]:
    with open(file_path, "r") as file:
        return json.load(file)


# Function to fetch and insert data
def fetch_and_insert_data(cursor: psycopg2.extensions.cursor, stocks):
    insert_query = (
        "INSERT INTO StockData (Symbol, Sector, Date, Open, High, Low, "
        "Close, Volume, DailyChangePercent) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
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

        if not start_date == end_date:
            stock_data = fetch_stock_data(symbol, start_date, end_date)

            # Prepare data for bulk insert
            data_to_insert = []
            # Get the last available closing price for this stock
            cursor.execute(
                "SELECT Close FROM StockData WHERE Symbol = %s ORDER BY Date DESC LIMIT 1",
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

            # Insert all rows in one go
            cursor.executemany(insert_query, data_to_insert)


def run_fetch_job(stocks: List = None):
    try:
        logging.info("Establishing database connection...")
        conn = connect_to_database()
        cursor = conn.cursor()

        logging.info("Fetching data for analysis...")
        if not stocks:
            stocks = read_stocks_from_json("stocks.json")
        fetch_and_insert_data(cursor, stocks)
        logging.info("Data fetched and inserted successfully...")
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        logging.error(f"Database error: {error}")
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")
