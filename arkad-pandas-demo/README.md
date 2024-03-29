# ARKAD Pandas Demo

## Introduction
Welcome to the ARKAD Pandas Demo! This project is a demonstration of an AI Assistant designed for Stock Market Investment Research. The only difference from [Arkad SQL Demo](https://github.com/Arkad-Finance/arkad-demo/tree/main/arkad-sql-demo) is that it uses pandas dataframes and hierarchical indexing over summaries of sectors and their respective stocks + separate Langchain Pandas Agent instead of storing all information about stocks market performance in single SQL database. The assistant is built using Langchain and Streamlit and it can retrieve a wide range of financial data, perform analysis, and execute Python code for complex calculations over pandas DataFrames.

This AI Assistant can provide company profile information, search for recent news and events, and perform analytical operations over stock market performance data stored in pandas DataFrames. It's an invaluable tool for investors, financial analysts, and anyone interested in stock market research.


## Note:
This is the first version of such an agent. Feedback and propositions are highly welcome. Feel free to reach out via [LinkedIn](https://www.linkedin.com/in/oleh-davydiuk/).


## Features
- **Company Profile Retrieval:** Get detailed information like market cap, latest earnings numbers, dividend yield and rate, operating and profit margins, etc.
- **News and Events Search:** Utilize Tavily Search to find the latest news, events, and M&A deals.
- **Python Code Execution:** Calculations on stock market data including candles, volume, net changes, plotting charts.
- **Streamlit Integration:** The assistant is accessible through a user-friendly Streamlit application. **Note:** plotting currently is not available when using streamlit for frontend interaction. To observe plotting capabilities, please refer to notebooks section.


## Important information
- **Data Source**: The agent uses yfinance to download market data. Adhere to Yahoo!'s terms of use regarding data usage.
- **Execution Caution**: The agent is capable of executing an arbitrary Python code. Use with caution.


## Prerequisites
- Python 3.10 or higher.
- Poetry for Python dependency management. Install Poetry following [this guide](https://www.digitalocean.com/community/tutorials/how-to-install-poetry-to-manage-python-dependencies-on-ubuntu-22-04).

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/Arkad-Finance/arkad-demo.git
    cd arkad-pandas-demo
    ```
2. Install dependencies using Poetry:

    - For running streamlit_front:
    ```bash
    cd streamlit_front
    poetry install
    ```
    - For running notebooks:
    ```bash
    cd notebooks
    poetry install
    ```
## Usage
- Current version of arkad-pandas-demo works with OpenAI models, will add open source models soon.
- If you want tavily search to work - create account at [Tavily website](https://tavily.com/) get API_KEY (there is free option) and paste it as tavily_api_key argument when creating agent.
- Another option is to define api keys in .env file, look at .envexample for reference.

### Basic Usage
- In this scenario pandas_market_agent will download data for stocks specified in pandas-market-agent/pandas_market_agent/agent/tools/storage/stocks.json.
    ```python
    import openai
    from pandas_market_agent.agent.agent import create_pandas_market_agent

    openai.api_key = “YOUR_OPENAI_API_KEY”
    llm = ChatOpenAI(temperature=0, model="gpt-4", streaming=True)

    agent_executor = create_pandas_market_agent(
        llm=llm,
    )

    response = agent_executor(
        {"input": "plot chart of NKE stock close price for last 5 dates you have in df", "chat_history":[]}
    )
    ```

- Also you may pass stocks list like this:
    ```python
    agent_executor = create_pandas_market_agent(
        llm=llm,
        stocks=["XOM", "CAT", "NKE"]
    )   
    ```

- In this case agent will download information for their specific industry from yfinance. You may specify sector manually:
    ```python
    agent_executor = create_pandas_market_agent(
        llm=llm,
        stocks=[{ "ticker": "XOM", "sector": "Oil" },
                { "ticker": "CAT", "sector": "Heavy Machinery" },
                { "ticker": "NKE", "sector": "Footwear" },
    )
    ```
- Stocks argument may be either list of stock tickers or list of dicts like above with keys “ticker” and “sector”. 