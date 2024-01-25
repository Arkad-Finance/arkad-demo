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
