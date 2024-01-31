# ARKAD SQL Demo

## Introduction
Welcome to the ARKAD SQL Demo! This project is a demonstration of an AI Assistant designed for Stock Market Investment Research. The assistant is built using Langchain and Streamlit, enabling it to retrieve a wide range of financial data, perform analysis, and even execute Python code for complex calculations.

This AI Assistant can provide company profile information, search for recent news and events, and perform analytical operations over stock market performance data stored in an SQL database. It's an invaluable tool for investors, financial analysts, and anyone interested in stock market research.

**Note:** This is the first version of such an agent. Feedback and propositions are highly welcome. Feel free to reach out via [LinkedIn](https://www.linkedin.com/in/oleh-davydiuk/).

## Features
- **Company Profile Retrieval:** Get detailed information like market cap, latest earnings numbers, dividend yield and rate, operating and profit margins, etc.
- **News and Events Search:** Utilize Tavily Search to find the latest news, events, and M&A deals.
- **Analytical Operations:** Perform operations on stock market data including candles, volume, and net changes.
- **Python Code Execution:** For more complex calculations and plotting charts, the agent can write and execute Python code.
- **Streamlit Integration:** The assistant is accessible through a user-friendly Streamlit application.

## Prerequisites
- Python 3.10 or higher.
- Poetry for Python dependency management. Install Poetry following [this guide](https://www.digitalocean.com/community/tutorials/how-to-install-poetry-to-manage-python-dependencies-on-ubuntu-22-04).

## Installation
- Clone the repository:
    ```bash
    git clone https://github.com/Arkad-Finance/arkad-demo.git
    cd arkad-sql-demo
- Install dependencies using Poetry:
    ```bash
    poetry install



Of course, I apologize for the oversight. Here's the complete README.md content in Markdown format:

markdown
Copy code
# ARKAD SQL Demo

## Introduction
Welcome to the ARKAD SQL Demo! This project is a demonstration of an AI Assistant designed for Stock Market Investment Research. The assistant is built using Langchain and Streamlit, enabling it to retrieve a wide range of financial data, perform analysis, and even execute Python code for complex calculations.

This AI Assistant can provide company profile information, search for recent news and events, and perform analytical operations over stock market performance data stored in an SQL database. It's an invaluable tool for investors, financial analysts, and anyone interested in stock market research.

**Note:** This is the first version of such an agent. Feedback and propositions are highly welcome. Feel free to reach out via [LinkedIn](https://www.linkedin.com/in/oleh-davydiuk/).

## Features
- **Company Profile Retrieval:** Get detailed information like market cap, latest earnings numbers, dividend yield and rate, operating and profit margins, etc.
- **News and Events Search:** Utilize Tavily Search to find the latest news, events, and M&A deals.
- **Analytical Operations:** Perform operations on stock market data including candles, volume, and net changes.
- **Python Code Execution:** For more complex calculations and plotting charts, the agent can write and execute Python code.
- **Streamlit Integration:** The assistant is accessible through a user-friendly Streamlit application.

## Prerequisites
- Python 3.10 or higher.
- Poetry for Python dependency management. Install Poetry following [this guide](https://www.digitalocean.com/community/tutorials/how-to-install-poetry-to-manage-python-dependencies-on-ubuntu-22-04).

## Installation

1. Clone the repository:
    ```bash
    git clone [your-repository-url]
    cd arkad-sql-demo
2. Install dependencies using Poetry:
    ```bash
    poetry install

## Usage
### Basic Usage
    ```python
    # Import the necessary modules and set up the AI model.
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
- In this scenario sql_market_agent will create SQLite database on disc and upload data for stocks specified in sql-market-agent/sql_market_agent/agent/tools/storage/stocks.json.

- Also you may pass stocks list like this:
    ```python
    agent_executor = create_sql_market_agent(
        llm=llm,
        preinitialize_database=True,
        stocks=[“XOM”, “CAT”, “NKE”]
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
Initialize the agent with or without a database.
Execute queries using the agent.
Running with Streamlit
Navigate to the streamlit_front directory:
bash
Copy code
cd streamlit_front
Run the Streamlit app:
bash
Copy code
streamlit run app.py
Running with Docker
Install Docker and Docker Compose.
Run:
bash
Copy code
docker compose up
Alternatively, use the run.sh script. Caution: This will stop the current Docker Compose stack.
bash
Copy code
source run.sh
Important Notes
Data Source: The agent uses yfinance to download market data. Adhere to Yahoo!'s terms of use regarding data usage.
Database Caution: Avoid using production databases and databases with sensitive data. Sandbox your environment wherever possible.
Execution Caution: The agent is capable of executing inserts, updates, deletes, and arbitrary Python code. Use with care.
Contact
For any feedback, propositions, or queries, please contact me on LinkedIn.