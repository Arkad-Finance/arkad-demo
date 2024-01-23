from pydantic.v1 import BaseModel, Field
from langchain.tools import BaseTool
from typing import Type
import yfinance as yf


class SymbolRelatedToolsInput(BaseModel):
    symbol: str = Field(..., description="Companies stock symbol")


class CompanyOverviewTool(BaseTool):
    name = "company_overview_tool"
    description = """Useful when you need to get a comprehensive company overview by its stock symbol.
        Metrics of interest include:
        Market Capitalization, Enterprise Value, Price-to-Earnings (P/E) Ratio, Price-to-Sales Ratio (P/S),
        Price-to-Book Ratio (P/B), Earnings Before Interest, Taxes, Depreciation, and Amortization (EBITDA),
        Revenue and Revenue Growth, Net Income and Growth, Earnings Growth, Dividend Yield and Rate, Operating and Profit Margins,
        Return on Assets (ROA) and Equity (ROE), Free Cash Flow, Debt-to-Equity Ratio, Current and Quick Ratios,
        Beta, 52-Week High and Low, Average Volume and many others. If there are ambiguous variants for answers, 
        think carefully which answer is most appropriate by reasoning from key in large dict you obtain."""
    args_schema: Type[BaseModel] = SymbolRelatedToolsInput

    def _run(self, symbol: str) -> dict:
        stock = yf.Ticker(symbol)
        info = stock.get_info()

        return info
