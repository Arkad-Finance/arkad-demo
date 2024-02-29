import pandas as pd
import pandas_datareader as pdr
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fetch configuration from .env file or set default values
START_DATE = os.getenv('START_DATE', '2013-01-01')
END_DATE = os.getenv('END_DATE', '2024-03-01')
LOG_FILE = os.getenv('LOG_FILE', 'data_fetch_log.log')

# Setup logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')

def fetch_fred_data(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    """
    Fetches data from the FRED API for a given symbol and date range.

    Parameters:
    symbol (str): The FRED symbol for the data series.
    start (datetime): Start date for the data retrieval.
    end (datetime): End date for the data retrieval.

    Returns:
    pd.DataFrame: Data fetched from FRED.
    """
    try:
        data = pdr.get_data_fred(symbol, start, end)
        if data.empty:
            raise ValueError(f"No data returned for {symbol}")
        return data
    except Exception as e:
        logging.error(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()

def main():
    # Define the symbols for the required data from FRED
    symbols = {
        '2-Year Treasury Constant Maturity Rate': 'DGS2',
        '10-Year Treasury Constant Maturity Rate': 'DGS10',
        'Unemployment Rate': 'UNRATE',
        'Consumer Price Index': 'CPIAUCSL'
    }

    # Convert string dates to datetime objects
    start_date = datetime.fromisoformat(START_DATE)
    end_date = datetime.fromisoformat(END_DATE)

    # Fetching and saving data
    for name, symbol in symbols.items():
        logging.info(f"Fetching data for {name}")
        data = fetch_fred_data(symbol, start_date, end_date)
        if not data.empty:
            file_name = f'{symbol}_data.csv'
            data.to_csv(file_name)
            logging.info(f"Data for {name} saved to {file_name}")
        else:
            logging.warning(f"No data fetched for {name}")

    logging.info("Data fetching process completed.")

if __name__ == "__main__":
    main()
