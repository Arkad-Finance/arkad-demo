from dotenv import load_dotenv
import os
import requests
from pydantic.v1 import BaseModel, Field
from langchain.tools import BaseTool
from typing import Type


load_dotenv()

ALPHA_VANTAGE_API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY")


class SymbolRelatedToolsInput(BaseModel):
    symbol: str = Field(..., description="Companies stock symbol")


class CompanyOverviewTool(BaseTool):
    name = "company_overview_tool"
    description = """Useful when you need to get company overview by it's stock symbol.
        Metrics of interest:
        Market Capitalization,
        EBITDA,
        Gross Profit TTM,
        Revenue TTM,
        EPS,
        PE Ratio,
        Profit Margin,
        Operating Margin TTM,
        Quarterly Earnings Growth YOY,
        Quarterly Revenue Growth YOY,
        When question is about getting some of those metrics specifically"""
    args_schema: Type[BaseModel] = SymbolRelatedToolsInput

    def _run(self, symbol: str) -> dict:
        url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={ALPHA_VANTAGE_API_KEY}"

        r = requests.get(url)
        data = r.json()

        return data
