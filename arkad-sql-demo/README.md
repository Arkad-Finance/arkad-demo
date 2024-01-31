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
    git clone [your-repository-url]
    cd arkad-sql-demo
-Install dependencies using Poetry:
    ```bash
    poetry install