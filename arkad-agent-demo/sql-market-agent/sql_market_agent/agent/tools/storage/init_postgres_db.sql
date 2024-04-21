-- Drop tables if they exist
DROP TABLE IF EXISTS StockData;

-- Create table for stock data
CREATE TABLE IF NOT EXISTS StockData (
    ID SERIAL PRIMARY KEY,
    Symbol TEXT NOT NULL,
    Sector TEXT,
    Date DATE NOT NULL,
    Open REAL NOT NULL,
    High REAL NOT NULL,
    Low REAL NOT NULL,
    Close REAL NOT NULL,
    Volume INTEGER NOT NULL,
    DailyChangePercent REAL NOT NULL,
    UNIQUE (Symbol, Date)  -- Adding a unique constraint
);

-- Drop tables if they exist
DROP TABLE IF EXISTS MacroMetricData;

-- Create table for macro data
CREATE TABLE IF NOT EXISTS MacroMetricData (
    ID SERIAL PRIMARY KEY,
    MacroMetric TEXT NOT NULL,
    Description TEXT NOT NULL,
    Date DATE NOT NULL,
    MacroMetricValue REAL NOT NULL,
    PeriodicChangePercent REAL,
    UNIQUE (MacroMetric, Description, Date)
);

-- Drop tables if they exist
DROP TABLE IF EXISTS StockFinancialData;

-- Create table for macro data
CREATE TABLE IF NOT EXISTS StockFinancialData (
    ID SERIAL PRIMARY KEY,
    Symbol TEXT NOT NULL,
    Sector TEXT NOT NULL,
    Year INTEGER NOT NULL,
    ReportType TEXT NOT NULL,
    Period TEXT NOT NULL,
    Amount REAL NOT NULL,
    QoQ REAL,
    YoY REAL,
    UNIQUE (Symbol, Sector, Year, ReportType, Period)
);

