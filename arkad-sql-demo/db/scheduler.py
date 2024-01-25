import schedule
from pathlib import Path
import time
from db_fetcher import run_fetch_job, read_stocks_from_json
import os
import logging

# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Database configuration
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB")
DB_USER = os.environ.get("POSTGRES_USER")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD")


def run_scheduled_fetching(db_connection_string: str):
    stocks_json_path = Path(__file__).parent / "stocks.json"
    stocks = read_stocks_from_json(stocks_json_path)
    run_fetch_job(db_connection_string=db_connection_string, stocks=stocks)
    logging.info(msg="Finished initial fetch")

    # Schedule the job every day at 00:00 AM UTC
    schedule.every().day.at("00:00").do(
        run_fetch_job, db_connection_string, False, stocks
    )
    logging.info(msg="Scheduled subsequent")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    db_connection_string = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    logging.info(msg="Starting scheduled fetching job...")
    run_scheduled_fetching(db_connection_string=db_connection_string)
