import requests
import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def download_json(url, headers):
    """Download JSON data from the given URL."""
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.HTTPError as errh:
        logging.error(f"Http Error: {errh}")
    except requests.exceptions.ConnectionError as errc:
        logging.error(f"Error Connecting: {errc}")
    except requests.exceptions.Timeout as errt:
        logging.error(f"Timeout Error: {errt}")
    except requests.exceptions.RequestException as err:
        logging.error(f"Error: {err}")
    return None

def transform_data(data):
    """Transform data to index by ticker."""
    transformed = {}
    for item in data.values():
        ticker = item.get('ticker')
        if ticker:
            transformed[ticker] = {
                'cik_str': item.get('cik_str'),
                'title': item.get('title')
            }
    return transformed

def save_to_json(data, file_name):
    """Save data to a JSON file."""
    try:
        with open(file_name, 'w') as file:
            json.dump(data, file, indent=4)
        logging.info(f"Data successfully saved to {file_name}")
    except IOError as e:
        logging.error(f"I/O error({e.errno}): {e.strerror}")

def main():
    """Main function to orchestrate the download and transformation process."""
    logging.info("Starting the download process.")
    headers = {'User-Agent': os.environ.get("EMAIL")}
    url = "https://www.sec.gov/files/company_tickers.json"

    json_data = download_json(url, headers)
    if json_data:
        transformed_data = transform_data(json_data)
        save_to_json(transformed_data, 'tickers_cik_info.json')
    logging.info("Process completed.")

if __name__ == "__main__":
    main()
