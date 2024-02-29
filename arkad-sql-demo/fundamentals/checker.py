import json
import pandas as pd
from datetime import datetime, date
from typing import List, Dict

def quarter_sort_key(quarter):
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



def create_financial_dataframe(records: List[Dict], ticker: str, sector: str, start_year: int, end_year: int):
    data_list = []

    available_data = {record['frame']: record['val'] for record in records if 'frame' in record}
    
    quarterly_frames = [f'CY{year}Q{q}' for year in range(2007, 2024) for q in range(1, 5)]
    for frame in quarterly_frames:
        if frame not in available_data:
            year = int(frame[2:6])
            quarter = frame[-2:]
            available_data[frame] = estimate_quarter(records, available_data, year, quarter)

    yearly_frames = [f'CY{year}' for year in range(2007, 2024)]
    for frame in yearly_frames:
        if frame not in available_data:
            year = int(frame[2:6])
            sum_quarters = sum(available_data.get(f'CY{year}Q{i}', 0) for i in range(1, 5))
            available_data[frame] = sum_quarters

    for frame, amount in available_data.items():
        year = int(frame[2:6])
        period = frame[-2:] if 'Q' in frame else 'FY'
        row = {
            "Ticker": ticker,
            "Sector": sector,
            "Year": year,
            "ReportType": "Revenue",
            "Period": period,
            "Amount": amount
        }
        data_list.append(row)

    df = pd.DataFrame(data_list)
    df = pd.DataFrame(data_list)
    df['QuarterSort'] = df['Period'].apply(quarter_sort_key)
    df = df.sort_values(by=['Year', 'QuarterSort'])
    df = df.drop(columns='QuarterSort')  # Remove the sorting helper column
    return df


def find_missing_frames(records: List[Dict]) -> Dict:
    # Initialize a dictionary to store the frames for each year
    frames_per_year = {}

    # Extracting frame values and identifying years from records
    for record in records:
        if 'frame' in record:
            frame = record['frame']
            year = frame[2:6] if 'Q' not in frame else frame[2:6]  # Extract year from frame
            frames_per_year.setdefault(year, set()).add(frame)

    # Define the expected frames for each year
    expected_frames = lambda year: {f'CY{year}', f'CY{year}Q1', f'CY{year}Q2', f'CY{year}Q3', f'CY{year}Q4'}

    # Identify missing frames for each year
    missing_frames = {}
    for year in frames_per_year:
        missing = expected_frames(year) - frames_per_year[year]
        if missing:
            missing_frames[year] = missing

    return missing_frames


with open("nvda_facts.json", "r") as file:
    records = json.load(file)
    records = records["facts"]["us-gaap"]["Revenues"]["units"]["USD"]

print(records)

missing_frames = find_missing_frames(records)
for year, frames in missing_frames.items():
    print(f"Year {year} is missing frames: {frames}")
start_year = 2007
end_year = 2024
df = create_financial_dataframe(records, 
                                ticker="NVDA", 
                                sector="Semiconductors", 
                                start_year=2007, 
                                end_year=2024)
df.to_csv("nvda_numbers.csv")
print(df)
