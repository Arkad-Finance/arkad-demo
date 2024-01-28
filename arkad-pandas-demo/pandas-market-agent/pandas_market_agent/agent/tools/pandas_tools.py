import logging
import pysqlite3 as sqlite3
import sys

sys.modules["sqlite3"] = sqlite3
from typing import List, Dict, Optional, Type
from langchain.tools import BaseTool
from langchain_core.language_models import BaseLanguageModel
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain.schema.document import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores.chroma import Chroma
from langchain.callbacks.manager import (
    CallbackManagerForToolRun,
)
from pydantic.v1 import BaseModel, Field
from pandas_market_agent.agent.tools.storage.data_fetcher import run_fetch_job
from pandas_market_agent.agent.tools.prompts.pandas_prompts import PREFIX


# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class PandasToolInput(BaseModel):
    query: str = Field(
        description="Query which requires constructing and "
        "running analytics code over pandas dataframe with historical market data "
        "for stocks of some sector"
    )


class PandasTool(BaseTool):
    name = "PandasTool"
    description = "Tool to process queries related to market sectors, "
    "and their stocks - both overall and specific market performance"
    args_schema: Type[BaseModel] = PandasToolInput

    llm: BaseLanguageModel = None
    stocks: Optional[List[Dict[str, str]]] = None
    sectors_data: List = []
    sector_dfs_agents: List = []
    summaries: List = []
    index_to_agent: Dict = {}
    db: Chroma = None

    def __init__(
        self, llm: BaseLanguageModel, stocks: Optional[List[Dict[str, str]]] = None
    ):
        # Call the parent class constructor with empty kwargs to bypass Pydantic validation
        super().__init__(**{})

        self.llm = llm
        self.stocks = stocks
        self.sectors_data = run_fetch_job(stocks=self.stocks)
        self.sector_dfs_agents = [
            create_pandas_dataframe_agent(
                llm=self.llm, df=sector_data["data"], prefix=PREFIX
            )
            for sector_data in self.sectors_data
        ]

        self.summaries = []
        for index, sector_data in enumerate(self.sectors_data):
            sector_summary = Document(
                page_content=f"Historical {list(sector_data['data'].columns)} data for {sector_data['data']['Symbol'].unique().tolist()} "
                f"stocks which belong to {sector_data['sector']} market sector",
                metadata={"sector_index": index},
            )
            self.summaries.append(sector_summary)

        self.index_to_agent = {
            index: sector_df_agent
            for index, sector_df_agent in enumerate(self.sector_dfs_agents)
        }
        self.db = Chroma.from_documents(self.summaries, OpenAIEmbeddings())

    def _run(
        self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        if run_manager:
            logging.info(f"Callback Manager of type {type(run_manager)}")
        else:
            logging.info("No callback managers mf")
        result = self.db.similarity_search(query=query, k=1)
        sector_index = result[0].metadata["sector_index"]
        sector_df_agent = self.index_to_agent[sector_index]
        response = sector_df_agent(
            query,
            callbacks=run_manager,
        )
        return response
