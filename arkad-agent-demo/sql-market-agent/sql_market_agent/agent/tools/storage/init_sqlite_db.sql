-- Drop tables if they exist
DROP TABLE IF EXISTS stockdata;

-- Create table for stock data
CREATE TABLE IF NOT EXISTS stockdata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    sector TEXT,
    date TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER NOT NULL,
    dailychangepercent REAL NOT NULL,
    UNIQUE (symbol, date)  -- Adding a unique constraint
);

-- Drop tables if they exist
DROP TABLE IF EXISTS macrometricdata;

-- Create table for macro data
CREATE TABLE IF NOT EXISTS macrometricdata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    macrometric TEXT NOT NULL,
    description TEXT NOT NULL,
    date TEXT NOT NULL,
    macrometricvalue REAL NOT NULL,
    periodicchangepercent REAL,
    UNIQUE (macrometric, description, date)
);

-- Drop tables if they exist
DROP TABLE IF EXISTS stockfinancialdata;

-- Create table for macro data
CREATE TABLE IF NOT EXISTS stockfinancialdata (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    sector TEXT NOT NULL,
    year INTEGER NOT NULL,
    reporttype TEXT NOT NULL,
    period TEXT NOT NULL,
    amount REAL NOT NULL,
    qoq REAL,
    yoy REAL,
    UNIQUE (symbol, sector, year, reporttype, period)
);
