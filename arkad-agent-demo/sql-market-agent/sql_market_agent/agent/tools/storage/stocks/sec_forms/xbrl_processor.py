import os
import requests
import json
import logging
import traceback
import sqlalchemy
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Optional
from pathlib import Path
from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as insert_postgres

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
HEADERS = {'User-Agent': os.environ.get("EMAIL")}
COMPANY_FACTS_URL = 'https://data.sec.gov/api/xbrl/companyfacts/CIK{}.json'
KEYS_TO_KEEP = {
    "us-gaap": [
        "Revenues", 
        "SalesRevenueNet", 
        "SalesRevenueGoodsNet",
        "SalesRevenueServicesNet",
        "RevenuesNetOfInterestExpense",
        "OperatingRevenues",
        "RevenueNotFromContractWithCustomer",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "TotalRevenue",
        "RevenueMineralSales",
        "OilAndGasRevenue",
        "RegulatedAndUnregulatedOperatingRevenue",
        "FranchiseRevenue",
        "InterestAndDividendRevenueOperating",
        "RealEstateRevenueNet",
        "AdvertisingRevenue"
    ]
}

def create_session(retries: int = 3, backoff_factor: float = 0.3) -> requests.Session:
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


def load_cik_info(file_path: str) -> Dict:
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except IOError as e:
        logging.error(f"Error reading {file_path}: {e}")
        return {}


def get_company_facts(session: requests.Session, cik: str):
    try:
        response = session.get(COMPANY_FACTS_URL.format(cik), headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Request failed for CIK {cik}: {e}")
        return None


def filter_facts(company_facts: Dict) -> List[Dict]:
    # Convert lists to sets and find intersection
    common_elements = set(KEYS_TO_KEEP["us-gaap"]) & set(company_facts["facts"]["us-gaap"])

    revenue_records = []
    # Check if there is any common element
    if common_elements:
        for element in common_elements:
            try:
                revenue_records = revenue_records + company_facts["facts"]["us-gaap"][element]["units"]["USD"]
            except KeyError as e:
                logging.warning(f"Key error while blending Revenues aliases: {e}")
        return revenue_records
    else:
        logging.warning(f"Missing required data categories for Revenues")
        return None


def save_facts_to_file(facts: Dict, symbol: str, facts_data_path: str):
    path_to_file = f"{facts_data_path}/{symbol}.json"
    try:
        with open(f"{facts_data_path}/{symbol}.json", 'w') as file:
            json.dump(facts, file, indent=4)
        logging.info(f"Data successfully saved to {path_to_file}")
    except IOError as e:
        logging.error(f"Error saving to {path_to_file}: {e}")


def quarter_sort_key(quarter: str) -> int:
    # Assigns a numeric value to each quarter for sorting
    return {'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4, 'FY': 5}.get(quarter, 0)


def months_diff(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month


def find_record_by_fp(records: List[Dict], year: int, fp: str) -> Dict:
    for record in records:
        if record['fp'] == fp and 'frame' not in record:
            start_date = datetime.strptime(record["start"], "%Y-%m-%d")
            end_date = datetime.strptime(record["end"], "%Y-%m-%d")
            if end_date.year == year and months_diff(start_date, end_date) > 5:
                return record
    return None


def calculate_historical_proportions(records: List[Dict], year: int, quarter: str) -> float:
    historical_totals = {q: [] for q in ['Q1', 'Q2', 'Q3', 'Q4']}
    for record in records:
        if 'frame' in record and record['frame'].startswith(f'CY{year - 1}') and 'Q' in record['frame']:
            historical_totals[record['frame'][-2:]].append(record['val'])

    avg_proportions = {q: sum(vals) / len(vals) if vals else 0 for q, vals in historical_totals.items()}
    total_avg = sum(avg_proportions.values())
    return avg_proportions[quarter] / total_avg if total_avg else 0


def estimate_quarter(records: List[Dict], available_data: Dict, year: int, quarter: str) -> float:
    next_q_record = find_record_by_fp(records, year, f'Q{int(quarter[1]) % 4 + 1}')
    next_q_val = available_data.get(f'CY{year}Q{int(quarter[1]) % 4 + 1}', 0)

    if quarter != 'Q4':
        if next_q_record and next_q_val:
            estimated_val = next_q_record['val'] - next_q_val
            return estimated_val if estimated_val > 0 else 0

    proportion = calculate_historical_proportions(records, year, quarter)
    fy_val = available_data.get(f'CY{year}', 0)
    estimated_val = fy_val * proportion if fy_val else 0

    if quarter == 'Q4' and fy_val:
        # Estimate Q4 by subtracting the sum of Q1, Q2, Q3 from FY if FY data is available
        q1_val = available_data.get(f'CY{year}Q1', fy_val / 4)
        q2_val = available_data.get(f'CY{year}Q2', fy_val / 4)
        q3_val = available_data.get(f'CY{year}Q3', fy_val / 4)
        return fy_val - (q1_val + q2_val + q3_val)

    if estimated_val == 0:
        for q in ['Q1', 'Q2', 'Q3', 'Q4']:
            if q != quarter and f'CY{year}{q}' in available_data:
                return available_data[f'CY{year}{q}']

        for offset in range(1, 3):
            neighbor_year_val = available_data.get(f'CY{year - offset}', 0) or available_data.get(f'CY{year + offset}', 0)
            if neighbor_year_val:
                return neighbor_year_val / 4

    return estimated_val if estimated_val > 0 else fy_val / 4


def process_and_insert_revenues_data_for_stock(session: sqlalchemy.orm.Session, 
                                               records: List[Dict], 
                                               symbol: str, 
                                               sector: str,
                                               earnings_data_path: Optional[str] = None,
                                               start_year: Optional[int] = None,
                                               end_year: Optional[int] = None):
    stock_table = sqlalchemy.Table(
        "stockfinancialdata", sqlalchemy.MetaData(), autoload_with=session.bind
    )
    data_rows = []

    temp_dict = {}
    quarterly_frames = [f'CY{year}Q{q}' for year in range(start_year, end_year) for q in range(1, 5)]
    yearly_frames = [f'CY{year}' for year in range(start_year, end_year)]
    year_to_available_frames = {year: {} for year in range(start_year, end_year)}

    # Consolidating records processing
    for record in records:
        frame = record.get("frame")
        val = record.get("val")
        if frame and val:
            # Update temp_dict for duplicate frame handling
            if frame in quarterly_frames + yearly_frames and (frame not in temp_dict or val > temp_dict[frame]):
                temp_dict[frame] = val

            # Update year_to_available_frames for missing quarters calculation
            if frame.startswith("CY"):
                year = int(frame[2:6])
                if year in year_to_available_frames:
                    year_to_available_frames[year][frame] = val

    available_data = temp_dict

    # Processing for quarters and years
    for frame in quarterly_frames:
        if frame not in available_data:
            year = int(frame[2:6])
            quarter = frame[-2:]
            available_data[frame] = estimate_quarter(records, available_data, year, quarter)

    for frame in yearly_frames:
        year = int(frame[2:6])
        quarters = [f"CY{year}Q{i}" for i in range(1, 5)]
        sum_quarters = sum(available_data.get(quarter, 0) for quarter in quarters)
        if frame not in available_data:
            available_data[frame] = sum_quarters
        elif not available_data[frame] == sum_quarters:
            current_years_frames = year_to_available_frames[year]
            # Determine available and missing quarters
            available_quarters = set(current_years_frames.keys()) & set(quarters)
            missing_quarters = set(quarters) - available_quarters

            # Calculate values for missing quarters
            if len(missing_quarters) == 1:
                missing_quarter = missing_quarters.pop()  # Get the missing quarter
                missing_value = available_data[frame] - sum(current_years_frames[q] for q in available_quarters)
                available_data[missing_quarter] = missing_value
            elif len(missing_quarters) in [2, 3]:
                total_available = sum(current_years_frames[q] for q in available_quarters)
                missing_value_each = (available_data[frame] - total_available) / len(missing_quarters)
                for mq in missing_quarters:
                    available_data[mq] = missing_value_each

    # Preparing data for insertion
    for frame, amount in available_data.items():
        year = int(frame[2:6])
        period = frame[-2:] if 'Q' in frame else 'FY'
        row = {
            "symbol": symbol,
            "sector": sector,
            "year": year,
            "reporttype": "Revenue",
            "period": period,
            "amount": amount
        }
        data_rows.append(row)
    
    # Sorting for YoY calculations
    df = pd.DataFrame(data_rows)
    df = df.sort_values(by=['symbol', 'sector', 'reporttype', 'period', 'year'])

    # Calculate YoY change for all periods including FY
    # We keep your YoY calculation as is since it's working correctly
    df['yoy'] = df.groupby(['symbol', 'sector', 'reporttype', 'period'])['amount'].pct_change(periods=1) * 100

    # Sorting for QoQ calculations
    df['quartersort'] = df['period'].apply(quarter_sort_key)
    df = df.sort_values(by=['year', 'quartersort'])
    df = df.drop(columns='quartersort')

    # Separate DataFrame for QoQ calculation (excluding 'FY')
    df_qoq = df[df['period'] != 'FY'].copy()

    # Calculate QoQ change
    df_qoq['qoq'] = df_qoq.groupby(['symbol', 'sector', 'reporttype'])['amount'].pct_change() * 100

    # Merge QoQ values back into the original DataFrame
    df = df.merge(df_qoq[['symbol', 'sector', 'year', 'reporttype', 'period', 'qoq']], on=['symbol', 'sector', 'year', 'reporttype', 'period'], how='left',  suffixes=('', '_y'))

    # Clean up the DataFrame to remove any unwanted columns from the merge
    df.drop(columns=[col for col in df.columns if col.endswith('_y')], inplace=True)

    if earnings_data_path:
        df.to_csv(f"{earnings_data_path}/{symbol}.csv")

    # Save and insert data
    data_to_insert = df.to_dict(orient='records')

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


def fetch_and_insert_revenues_data(session: sqlalchemy.orm.Session, 
                                   stocks: List[Dict[str, str]], 
                                   earnings_data_path: Optional[str] = None,
                                   facts_data_path: Optional[str] = None,
                                   start_year: Optional[int] = None,
                                   end_year: Optional[int] = None):
    cik_file_path = Path(__file__).parent / "tickers_cik_info.json"
    cik_info = load_cik_info(cik_file_path)
    requests_session = create_session()

    for stock in stocks:
        symbol = stock['ticker']
        sector = stock['sector']
        cik = str(cik_info.get(symbol, {}).get("cik_str", "")).zfill(10)
        logging.info(f"Processing {symbol} with CIK {cik}")

        company_facts = get_company_facts(requests_session, cik)

        if not company_facts:
            logging.warn(f"No company facts for {symbol}, skipping...")
            continue

        if "us-gaap" in company_facts["facts"]:
            filtered_facts = filter_facts(company_facts)
            if filtered_facts:
                try:
                    if facts_data_path:
                        save_facts_to_file(filtered_facts, symbol, facts_data_path)

                    process_and_insert_revenues_data_for_stock(session=session,
                                                               records=filtered_facts,
                                                               symbol=symbol, 
                                                               sector=sector,
                                                               earnings_data_path=earnings_data_path,
                                                               start_year=start_year, 
                                                               end_year=end_year)
                except KeyError as e:
                    # Log the error with stack trace
                    logging.error(f"Key error: {e}\n{traceback.format_exc()}")
                    logging.info(f"Skipping {symbol} due to missing revenue data.")
            else:
                logging.info(f"Skipping {symbol} due to missing revenue data.")
        else:
            logging.warn(f"No 'us-gaap' data in {symbol} facts, skipping...")
