import yfinance as yf
import pandas as pd
import pandas_datareader as pdr
import sqlalchemy
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy import text, insert, select
from sqlalchemy.dialects.postgresql import insert as insert_postgres


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def calculate_periodic_change(current_value: float, previous_value: float) -> float:
    return (
        (current_value - previous_value) / previous_value * 100
        if previous_value is not None
        else None
    )


def get_last_date_for_bond(session: sqlalchemy.orm.Session, bond: str) -> datetime.date:
    result = session.execute(
        text("SELECT MAX(Date) FROM BondData WHERE Bond = :bond"),
        {"bond": bond},
    ).fetchone()
    last_date = None
    if result:
        last_date = (
            datetime.strptime(result[0], "%Y-%m-%d").date()
            if isinstance(result[0], str)
            else result[0]
        )

    return last_date


def get_last_yield_for_bond(
    session: sqlalchemy.orm.Session, bond_table: sqlalchemy.Table, bond: str
) -> float:
    last_yield_query = (
        select(bond_table.c.yield_)
        .where(bond_table.c.bond == bond)
        .order_by(bond_table.c.date.desc())
        .limit(1)
    )
    result = session.execute(last_yield_query).fetchone()
    return result[0] if result else None


def get_last_date_for_macro_metric(session: sqlalchemy.orm.Session, macro_metric: str) -> datetime.date:
    result = session.execute(
        text("SELECT MAX(Date) FROM MacroMetricData WHERE MacroMetric = :macro_metric"),
        {"macro_metric": macro_metric},
    ).fetchone()
    last_date = None
    if result:
        last_date = (
            datetime.strptime(result[0], "%Y-%m-%d").date()
            if isinstance(result[0], str)
            else result[0]
        )

    return last_date


def get_last_value_for_macro_metric(
    session: sqlalchemy.orm.Session, macro_metric_table: sqlalchemy.Table, macro_metric: str
) -> float:
    last_macrometricvalue_query = (
        select(macro_metric_table.c.macrometricvalue)
        .where(macro_metric_table.c.macrometric == macro_metric)
        .order_by(macro_metric_table.c.date.desc())
        .limit(1)
    )
    result = session.execute(last_macrometricvalue_query).fetchone()
    return result[0] if result else None


def fetch_fred_data(symbol: str, start: str, end: str) -> pd.DataFrame:
    try:
        data = pdr.get_data_fred(symbol, start, end)
        if data.empty:
            raise ValueError(f"No data returned for {symbol}")
        return data
    except Exception as e:
        logging.error(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()


def fetch_cpi_data(session: sqlalchemy.orm.Session) -> pd.DataFrame:
    MacroData = sqlalchemy.Table('macrodata', sqlalchemy.MetaData(), autoload_with=session.bind)
    end_date = datetime.now()
    last_date_query = select([MacroData.c.date]).order_by(MacroData.c.date.desc()).limit(1)
    last_date_result = session.execute(last_date_query).fetchone()
    last_date = last_date_result[0] if last_date_result else datetime(2013, 1, 1)

    return fetch_fred_data('CPIAUCSL', last_date + timedelta(days=1), end_date)


def fetch_and_insert_bonds_data(session: sqlalchemy.orm.Session, bonds: List[Dict[str, str]]):
    bond_table = sqlalchemy.Table('bonddata', sqlalchemy.MetaData(), autoload_with=session.bind)

    for bond in bonds:
        symbol = bond["symbol"]
        description = bond["description"]
        last_date = get_last_date_for_bond(session, symbol)
        start_date = (
            (last_date + timedelta(days=1))
            if last_date
            else datetime(2013, 1, 1).date()
        )
        end_date = datetime.now().date()
        if start_date < end_date:
            bond_data = fetch_fred_data(
                symbol, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
            )

            prev_yield = get_last_yield_for_bond(session, bond_table, symbol)
            data_to_insert = []
            for index, row in bond_data.iterrows():
                daily_change = calculate_periodic_change(row[symbol], prev_yield)
                prev_yield = row[symbol]
                if daily_change is not None:
                    data_to_insert.append(
                        {
                            "bond": symbol,
                            "description": description,
                            "date": index.strftime("%Y-%m-%d"),
                            "yield_": row[symbol],
                            "dailychangepercent": daily_change,
                        }
                    )

            if session.bind.dialect.name == "postgresql":
                statement = (
                    insert_postgres(bond_table)
                    .values(data_to_insert)
                    .on_conflict_do_nothing()
                )
            elif session.bind.dialect.name == "sqlite":
                statement = (
                    insert(bond_table).values(data_to_insert).prefix_with("OR IGNORE")
                )

            session.execute(statement)
            session.commit()


def fetch_and_insert_macro_metrics_data(session: sqlalchemy.orm.Session, macro_metrics: List[Dict[str, str]]):
    macro_metric_table = sqlalchemy.Table('macrometricdata', sqlalchemy.MetaData(), autoload_with=session.bind)

    for macro_metric in macro_metrics:
        symbol = macro_metric["symbol"]
        description = macro_metric["description"]
        last_date = get_last_date_for_macro_metric(session, symbol)
        start_date = (
            (last_date + timedelta(days=1))
            if last_date
            else datetime(2013, 1, 1).date()
        )
        end_date = datetime.now().date()
        if start_date < end_date:
            macro_metric_data = fetch_fred_data(
                symbol, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
            )

            prev_value = get_last_value_for_macro_metric(session, macro_metric_table, symbol)
            data_to_insert = []
            for index, row in macro_metric_data.iterrows():
                periodic_change = calculate_periodic_change(row[symbol], prev_value)
                prev_value = row[symbol]
                if periodic_change is not None:
                    data_to_insert.append(
                        {
                            "macrometric": symbol,
                            "description": description,
                            "date": index.strftime("%Y-%m-%d"),
                            "macrometricvalue": row[symbol],
                            "periodicchangepercent": periodic_change,
                        }
                    )

            if session.bind.dialect.name == "postgresql":
                statement = (
                    insert_postgres(macro_metric_table)
                    .values(data_to_insert)
                    .on_conflict_do_nothing()
                )
            elif session.bind.dialect.name == "sqlite":
                statement = (
                    insert(macro_metric_table).values(data_to_insert).prefix_with("OR IGNORE")
                )

            session.execute(statement)
            session.commit()
