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
