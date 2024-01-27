from pathlib import Path
import json
from typing import List, Dict
import pandas as pd
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
import yfinance as yf
import logging

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def read_stocks_from_json(file_path: str) -> json:
    with open(file_path, "r") as file:
        return json.load(file)


def run_fetch_job(stocks: List[Dict[str, str]] = None) -> List:
    if not stocks:
        logging.info(
            msg="No stocks provided, loading default stocks list from stocks.json"
        )
        stocks_json_path = Path(__file__).parent / "stocks.json"
        stocks = read_stocks_from_json(stocks_json_path)

    sector_dataframes = {}

    for stock in stocks:
        ticker = stock["ticker"]
        sector = stock["sector"]

        # Fetching sector from yfinance if it's not provided
        if not sector:
            sector = yf.Ticker(ticker).get_info().get("industry", "Other")

        # Fetching OHLC data for the stock
        data = yf.Ticker(ticker).history(period="1mo")

        # Calculating DailyChangePercent and adding Symbol column
        data["DailyChangePercent"] = data["Close"].pct_change() * 100
        data["Symbol"] = ticker

        # Adding the sector to the dataframe
        data["Sector"] = sector

        # Reset index to make 'Date' a column and format it
        data.reset_index(inplace=True)
        data["Date"] = data["Date"].dt.strftime("%Y-%m-%d")

        # Concatenating dataframes within the same sector
        if sector not in sector_dataframes:
            sector_dataframes[sector] = data
        else:
            sector_dataframes[sector] = pd.concat([sector_dataframes[sector], data])

    # Drop duplicates and create the final list format
    final_data = []
    for sector, df in sector_dataframes.items():
        df = df.drop_duplicates(subset=["Symbol", "Date"])
        df.reset_index(inplace=True, drop=True)
        final_data.append({"sector": sector, "data": df})

    logging.info(msg="Stocks data loaded successfully")

    return final_data
