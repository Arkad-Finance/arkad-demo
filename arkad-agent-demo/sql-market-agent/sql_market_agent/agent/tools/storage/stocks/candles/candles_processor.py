import yfinance as yf
import pandas as pd
import sqlalchemy
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import text, insert, select
from sqlalchemy.dialects.postgresql import insert as insert_postgres
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def fetch_stock_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    stock = yf.Ticker(symbol)
    return stock.history(start=start_date, end=end_date)


def calculate_periodic_change(current_value: float, previous_value: float) -> float:
    return (
        (current_value - previous_value) / previous_value * 100
        if previous_value is not None
        else None
    )


def get_last_date_for_stock(session: sqlalchemy.orm.Session, symbol: str) -> datetime.date:
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


def fetch_and_insert_stocks_data(
    session: sqlalchemy.orm.Session, stocks: List[Dict[str, str]], 
    start_date: Optional[str] = "2023-01-01",
    end_date: Optional[str] = None,
):
    stock_table = sqlalchemy.Table(
        "stockdata", sqlalchemy.MetaData(), autoload_with=session.bind
    )

    for stock in stocks:
        symbol = stock["ticker"]
        sector = stock["sector"]
        if not sector:
            sector = yf.Ticker(symbol).get_info().get("industry", "")
        last_date = get_last_date_for_stock(session, symbol)
        start_date_local = (
            (last_date + timedelta(days=1))
            if last_date
            else datetime.strptime(start_date, "%Y-%m-%d").date()
        )
        end_date_local= datetime.now().date() if not end_date else datetime.strptime(end_date, "%Y-%m-%d").date()
        if start_date < end_date:
            stock_data = fetch_stock_data(
                symbol, start_date_local.strftime("%Y-%m-%d"), end_date_local.strftime("%Y-%m-%d")
            )

            prev_close = get_last_close_for_stock(session, stock_table, symbol)
            data_to_insert = []
            for index, row in stock_data.iterrows():
                daily_change = calculate_periodic_change(row["Close"], prev_close)
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
            