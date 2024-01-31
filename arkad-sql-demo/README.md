# ARKAD SQL Demo

## Introduction
Welcome to the ARKAD SQL Demo! This project is a demonstration of an AI Assistant designed for Stock Market Investment Research. The assistant is built using Langchain and Streamlit and it can retrieve a wide range of financial data, perform analysis, and execute SQL and Python code for complex calculations.

This AI Assistant can provide company profile information, search for recent news and events, and perform analytical operations over stock market performance data stored in an SQL database. It's an invaluable tool for investors, financial analysts, and anyone interested in stock market research.


## Note:
This is the first version of such an agent. Feedback and propositions are highly welcome. Feel free to reach out via [LinkedIn](https://www.linkedin.com/in/oleh-davydiuk/).


## Features
- **Company Profile Retrieval:** Get detailed information like market cap, latest earnings numbers, dividend yield and rate, operating and profit margins, etc.
- **News and Events Search:** Utilize Tavily Search to find the latest news, events, and M&A deals.
- **Analytical Operations:** Perform operations on stock market data including candles, volume, and net changes.
- **Python Code Execution:** For more complex calculations and plotting charts, the agent can write and execute Python code.
- **Streamlit Integration:** The assistant is accessible through a user-friendly Streamlit application.


## Important information
- **Data Source**: The agent uses yfinance to download market data. Adhere to Yahoo!'s terms of use regarding data usage.
- **Database Caution**: Avoid using production databases and databases with sensitive data. Sandbox your environment wherever possible.
- **Execution Caution**: The agent is capable of executing inserts, updates, deletes, and arbitrary Python code. Use with caution.


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
    ```bash
    poetry install
    ```
## Usage
- Current version of arkad-sql-demo works with OpenAI models, will add open source models soon.
- If you want tavily search to work - create account at [Tavily website](https://tavily.com/) get API_KEY (there is free option) and paste it as tavily_api_key argument when creating agent.
- Another option is to define all api keys and db connection arguments in .env file, look at .envexample for reference.

### Basic Usage
- In this scenario sql_market_agent will create SQLite database on disc and upload data for stocks specified in sql-market-agent/sql_market_agent/agent/tools/storage/stocks.json.
    ```python
    import openai
    from sql_market_agent.agent.agent import create_sql_market_agent

    openai.api_key = “YOUR_OPENAI_API_KEY”
    llm = ChatOpenAI(temperature=0, model="gpt-4", streaming=True)

    agent_executor = create_sql_market_agent(
        llm=llm,
        preinitialize_database=True,
    )

    response = agent_executor(
        {"input": user_input, "chat_history":[]}
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

### If you want to work with your up and running postgres database
- In this scenario sql market agent will connect to your database, figure out its schema and will be capable of running sql queries over your data. 
Note, that we don’t set preinitialize_database to True (which is False by default) because we do not want to drop if exists and create stockdata table in your database. If you want to do that - you may set preinitialize_database to True explicitly. In that scenario you either pass a stocks list for which you want to download data or sql agent will use default stocks from sql-market-agent/sql_market_agent/agent/tools/storage/stocks.json. 
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

    llm = ChatOpenAI(temperature=0, model="gpt-4", streaming=True)

    # Create postgres connection string:
    db_connection_string = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    agent_executor = create_sql_market_agent(
        llm=llm,
        db_connection_string=db_connection_string,
    )
    ```

### Run with streamlit:
- Go to streamlit_front directory and run streamlit app:
    ```bash 
    cd streamlit_front
    streamlit run app.py
    ```

### Run with docker:
- Install docker and docker compose.
- This will:
1. Spin a local postgres instance
2. Run job which will fetch data for stocks defined in db/stocks.json
3. Schedule subsequent fetching, currently for daily OHLCV data
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