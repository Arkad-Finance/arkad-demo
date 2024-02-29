import os
import requests
import json
import logging
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
HEADERS = {'User-Agent': os.environ.get("EMAIL")}
COMPANY_FACTS_URL = 'https://data.sec.gov/api/xbrl/companyfacts/CIK{}.json'
TICKERS_FILE = 'stocks.json'
CIK_FILE = 'tickers_cik_info.json'
KEYS_TO_KEEP = {
    "dei": ["EntityCommonStockSharesOutstanding"],
    "us-gaap": ["Revenues", "EarningsPerShareBasic"]
}


def create_session(retries=3, backoff_factor=0.3):
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=(500, 502, 504),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def load_tickers(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except IOError as e:
        logging.error(f"Error reading {file_path}: {e}")
        return []


def load_cik_info(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except IOError as e:
        logging.error(f"Error reading {file_path}: {e}")
        return {}


def get_company_facts(session, cik):
    try:
        response = session.get(COMPANY_FACTS_URL.format(cik), headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Request failed for CIK {cik}: {e}")
        return None


def filter_facts(company_facts):
    try:
        dei_data = {key: company_facts["facts"]["dei"][key] for key in KEYS_TO_KEEP["dei"]}

        # Simplified handling for 'Revenues'
        revenue_key = None
        for key in ["Revenues", "RevenueNotFromContractWithCustomer", "RevenueFromContractWithCustomerExcludingAssessedTax"]:
            if key in company_facts["facts"]["us-gaap"]:
                revenue_key = key
                break

        if not revenue_key:
            return None  # Skip this ticker if no suitable revenue data is found

        us_gaap_data = {key: company_facts["facts"]["us-gaap"][key] for key in KEYS_TO_KEEP["us-gaap"] if key != "Revenues"}
        us_gaap_data["Revenues"] = company_facts["facts"]["us-gaap"][revenue_key]

        filtered_facts = {"dei": dei_data, "us-gaap": us_gaap_data}
        company_facts["facts"] = filtered_facts
        return company_facts
    except KeyError as e:
        logging.warning(f"Missing required data category: {e}")
        return None


def save_facts_to_file(facts, ticker):
    file_path = f"forms_data/{ticker}_facts.json"
    try:
        with open(file_path, 'w') as file:
            json.dump(facts, file, indent=4)
        logging.info(f"Data successfully saved to {file_path}")
    except IOError as e:
        logging.error(f"Error saving to {file_path}: {e}")


def process_tickers():
    tickers = load_tickers(TICKERS_FILE)
    cik_info = load_cik_info(CIK_FILE)
    session = create_session()

    for ticker_info in tickers:
        ticker = ticker_info['ticker']
        cik = str(cik_info.get(ticker, {}).get("cik_str", "")).zfill(10)
        logging.info(f"Processing {ticker} with CIK {cik}")

        company_facts = get_company_facts(session, cik)

        if company_facts:
            filtered_facts = filter_facts(company_facts)
            if filtered_facts:
                save_facts_to_file(filtered_facts, ticker)
            else:
                logging.info(f"Skipping {ticker} due to missing revenue data.")


if __name__ == "__main__":
    process_tickers()
