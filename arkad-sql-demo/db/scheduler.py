import schedule
import time
from db_fetcher import run_fetch_job
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


def env_vars_set() -> bool:
    """Check if all required environment variables are set."""
    required_vars = [DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD]
    return all(required_vars)


def run_scheduled_fetching():
    run_fetch_job()
    logging.info(msg="Finished initial fetch...")

    # Schedule the job every day at 00:00 AM UTC
    schedule.every().day.at("00:00").do(run_fetch_job)
    logging.info(msg="Scheduled subsequent...")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    if env_vars_set():
        logging.info(msg="Starting scheduled fetching job...")
        run_scheduled_fetching()
    else:
        logging.info(
            msg="Please, provide DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD inside .env file and rerun service"
        )
