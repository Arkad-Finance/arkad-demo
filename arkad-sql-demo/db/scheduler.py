import schedule
import time
from db_fetcher import run_fetch_job


def run_scheduled_fetching():
    run_fetch_job()

    # Schedule the job every day at 00:00 AM UTC
    schedule.every().day.at("00:00").do(run_fetch_job)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    run_scheduled_fetching()
