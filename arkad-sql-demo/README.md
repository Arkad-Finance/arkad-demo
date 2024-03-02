# ARKAD SQL Demo

## Introduction
Welcome to the ARKAD SQL Demo! This project is a demonstration of an AI Assistant designed for Stock Market Investment Research. The assistant is built using Langchain and Streamlit and it can retrieve a wide range of financial data, perform analysis, and execute SQL and Python code for complex calculations.

This AI Assistant can provide company profile information, search for recent news and events, and perform analytical operations over stock market performance data stored in an SQL database. It's an invaluable tool for investors, financial analysts, and anyone interested in stock market research.


## Note:
This is the first version of such an agent. Feedback and propositions are highly welcome. Feel free to reach out via [LinkedIn](https://www.linkedin.com/in/oleh-davydiuk/).


## Features
- **Company Profile Retrieval:** Get detailed information like market cap, latest earnings numbers, dividend yield and rate, operating and profit margins, etc.
- **News and Events Search:** Utilize Tavily Search to find the latest news, events, and M&A deals.
- **Analytical Operations:** Ask questions and give tasks to Arkad regarding financial markets analysis in natural language. Arkad can perform complex calculations and plot charts and graphs over financial data, which includes: 
  - **Stocks:** 
    - Market performance data (OHLCV data)
    - Revenue data from yearly and quarterly reports (both 10K and 10Q)
  - **Macro Indicators:** 
    - Unemployment Rate
    - CPI
    - Federal Funds Target and Effective rates
    - Bonds yields and spreads, etc.
- **Python Code Execution:** For more complex calculations and plotting charts, the agent can write and execute Python code.
- **Streamlit Integration:** The assistant is accessible through a user-friendly Streamlit application. Plotting is also available.


## Important information
- **Data Source**: The agent uses yfinance and FRED API to download market data. Adhere to Yahoo!'s and FREDs terms of use regarding data usage. You need to obtain [FRED API key](https://fred.stlouisfed.org/) and place it into your .env for code to be able to fetch macro indicators data. Arkad uses SEC's XBRL [eXtensible Business Reporting Language](https://en.wikipedia.org/wiki/XBRL) API to parse reports data. You need to paste your email into .env file for code to fetch and parse quarterly and annual revenue data from SEC API.
- **Database Caution**: Avoid using production databases and databases with sensitive data. Sandbox your environment wherever possible.
- **Execution Caution**: The agent is capable of executing inserts, updates, deletes, and arbitrary Python code. Code execution is sandboxed using [E2B](https://e2b.dev/docs). You need to obtain your API key there and place it into your .env file for code execution sandboxing. If otherwise, you want 
your code to run using local (unsafe) Python REPL tool - go to ***sql-market-agent/sql_market_agent/agent/agent.py***, uncomment line with ***PythonREPLTool*** and comment ***SandboxTool*** in ***get_tools*** function:
```python
# repl_tool = SandboxTool()
repl_tool = PythonREPLTool()
```


## Prerequisites
- Python 3.10 or higher.
- Poetry for Python dependency management. Install Poetry following [this guide](https://www.digitalocean.com/community/tutorials/how-to-install-poetry-to-manage-python-dependencies-on-ubuntu-22-04).

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/Arkad-Finance/arkad-demo.git
    cd arkad-sql-demo
    ```
2. Install dependencies using Poetry:

     - For running streamlit_front:
      - In one terminal
        ```bash
        cd streamlit_front
        poetry install
        streamlit run app.py
        ```
      - In another start http server to render interactive plots:
        ```bash
        source run_server.sh
        ```

    - For running notebooks (interactive plots will be saved under charts folder in .html format):
    ```bash
    cd notebooks
    poetry install
    ```
## Usage
- Current version of arkad-sql-demo works with OpenAI and Open Source models like Mistral, although, practically performance with OpenAI models is much better now. We are working hard to bridge the performance gap between OpenAI and Open Source agents and it will definitely happen in nearest future :)
- If you want tavily search to work - create account at [Tavily website](https://tavily.com/) get API_KEY (there is free option) and paste it as tavily_api_key argument when creating agent or add it to your .env.
- Another option is to define all api keys and db connection arguments in .env file, look at .envexample for reference.

### Basic Usage
- In this scenario sql_market_agent will create SQLite database on disc and upload data for stocks and bonds/macro data specified in ***sql-market-agent/sql_market_agent/agent/tools/storage/stocks.json*** and ***sql-market-agent/sql_market_agent/agent/tools/storage/macro_metrics.json***
    ```python
    import openai
    from sql_market_agent.agent.agent import create_sql_market_agent

    openai.api_key = “YOUR_OPENAI_API_KEY”
    # For using open ai models
    openai.api_key = OPENAI_API_KEY
    llm = ChatOpenAI(temperature=0, 
                    model="gpt-4-0125-preview", 
                    streaming=True, 
                    model_kwargs={"seed": 123})
    sql_llm = ChatOpenAI(temperature=0, 
                    model="gpt-4-0125-preview", 
                    streaming=True, 
                    model_kwargs={"seed": 123})
    code_llm = ChatOpenAI(temperature=0, 
                    model="gpt-4-0125-preview", 
                    streaming=True, 
                    model_kwargs={"seed": 123})


    agent_executor = create_sql_market_agent(
        llm=llm,
        sql_llm=sql_llm,
        code_llm=code_llm,
        agent_type=AgentType.OPENAI_FUNCTIONS,
        preinitialize_database=True,
    )
    ```

- Also you may pass stocks list like this:
    ```python
    agent_executor = create_sql_market_agent(
        llm=llm,
        preinitialize_database=True,
        stocks=["XOM", "CAT", "NKE"]
    )   
    ```

- In this case agent will download information for their specific industry from yfinance. You may specify sector manually:
    ```python
    agent_executor = create_sql_market_agent(
        llm=llm,
        preinitialize_database=True,
        stocks=[{ "ticker": "XOM", "sector": "Oil" },
                { "ticker": "CAT", "sector": "Heavy Machinery" },
                { "ticker": "NKE", "sector": "Footwear" },
    )
    ```
- Stocks argument may be either list of stock tickers or list of dicts like above with keys “ticker” and “sector”.
- You can also pass ***macro_metrics*** argument which MUST be list of dics in following format (taken from ***sql-market-agent/sql_market_agent/agent/tools/storage/macro_metrics.json***):
```json
[
    {"symbol": "UNRATE", "description": "Unemployment Rate"},
    {"symbol": "CPIAUCSL", "description": "Consumer Price Index"},
    {"symbol": "DFF", "description": "Federal Funds Effective Rate"},
    {"symbol": "DFEDTARU", "description": "Federal Funds Target Range - Upper Limit"},
    {"symbol": "DFEDTARL", "description": "Federal Funds Target Range - Lower Limit"},
    {"symbol": "DJIA", "description": "Dow Jones Industrial Average"},
    {"symbol": "SP500", "description": "S&P500 Index"},
    {"symbol": "A191RL1Q225SBEA", "description": "Real Gross Domestic Product"},
    {"symbol": "GFDEBTN", "description": "Federal Debt: Total Public Debt"},
    {"symbol": "T10Y2Y", "description": "10-Year Treasury Constant Maturity Minus 2-Year Treasury Constant Maturity. Precalculated spread between yields of 10y and 2y treasury bonds"},
    {"symbol": "T10Y3M", "description": "10-Year Treasury Constant Maturity Minus 3-Month Treasury Constant Maturity. Precalculated spread between yields of 10y and 3m treasury bonds"},
    {"symbol": "DGS3MO", "description": "Market Yield on U.S. Treasury Securities at 3-Month Constant Maturity, Quoted on an Investment Basis"},
    {"symbol": "DGS6MO", "description": "Market Yield on U.S. Treasury Securities at 6-Month Constant Maturity, Quoted on an Investment Basis"},
    {"symbol": "DGS1", "description": "Market Yield on U.S. Treasury Securities at 1-Year Constant Maturity, Quoted on an Investment Basis"},
    {"symbol": "DGS2", "description": "Market Yield on U.S. Treasury Securities at 2-Year Constant Maturity, Quoted on an Investment Basis"},
    {"symbol": "DGS5", "description": "Market Yield on U.S. Treasury Securities at 5-Year Constant Maturity, Quoted on an Investment Basis"},
    {"symbol": "DGS10", "description": "Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity, Quoted on an Investment Basis"},
    {"symbol": "DGS20", "description": "Market Yield on U.S. Treasury Securities at 20-Year Constant Maturity, Quoted on an Investment Basis"},
    {"symbol": "DGS30", "description": "Market Yield on U.S. Treasury Securities at 30-Year Constant Maturity, Quoted on an Investment Basis"}
]
```

### If you want to work with your up and running postgres or SQLite database (below is postgres example, to use SQLite simply give proper db_connection_string)
- In this scenario sql market agent will connect to your database, figure out its schema and will be capable of running sql queries over your data. 
If you want sql_market_agent to fill your database with data discussed above - set ***preinitialize_database*** to ***True*** (which is ***False*** by default). If it is ***False*** - database will be used as is. Also note ***earnings_data_path*** and ***facts_data_path*** arguments. If those are specified - ***Revenues*** data from earnings reports will be saved in those files - raw data into ***facts_data_path*** in json format and csv data for FY, Q1, Q2, Q3 and Q4 reports inside ***earnings_data_path***.  
    ```python
    from langchain_openai.chat_models import ChatOpenAI
    from sql_market_agent.agent.agent import create_sql_market_agent
    from dotenv import load_dotenv

    load_dotenv()

    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
    DB_PORT = os.getenv("POSTGRES_PORT", "5432")
    DB_NAME = os.environ.get("POSTGRES_DB")
    DB_USER = os.environ.get("POSTGRES_USER")
    DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD")

    openai.api_key = OPENAI_API_KEY

    llm = ChatOpenAI(temperature=0, 
                    model="gpt-4-0125-preview", 
                    streaming=True, 
                    model_kwargs={"seed": 123})
    sql_llm = ChatOpenAI(temperature=0, 
                    model="gpt-4-0125-preview", 
                    streaming=True, 
                    model_kwargs={"seed": 123})
    code_llm = ChatOpenAI(temperature=0, 
                    model="gpt-4-0125-preview", 
                    streaming=True, 
                    model_kwargs={"seed": 123})

    # Create postgres connection string:
    db_connection_string = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    agent_executor = create_sql_market_agent(
        llm=st.session_state["llm"],
        sql_llm=st.session_state["sql_llm"],
        code_llm=st.session_state["code_llm"],
        agent_type=AgentType.OPENAI_FUNCTIONS,
        preinitialize_database=True,
        db_connection_string=db_connection_string,
        earnings_data_path="./earnings",
        facts_data_path="./facts",
    )
    ```

### Run with streamlit:
- Go to streamlit_front directory and run streamlit app:
    - In one terminal
        ```bash
        cd streamlit_front
        poetry install
        streamlit run app.py
        ```
    - In another start http server to render interactive plots:
        ```bash
        source run_server.sh
        ```

### Run with docker:
- Install docker and docker compose.
- This will:
1. Spin a local postgres instance
2. Run job which will fetch data for stocks and marco/bonds metrics defined in db/stocks.json and db/macro_metrics.json
3. Schedule subsequent fetching
4. Run streamlit frontend for interaction
- Please, setup api keys and db connection arguments in .env file, look at .envexample for reference.
- Run inside arkad-sql-demo directory:
    ```bash
    docker compose up
    ```

- Or you can execute run.sh script. Note, that it will first run docker compose down -v to stop current docker compose stack, use with caution:
    ```bash
    source run.sh
    ```