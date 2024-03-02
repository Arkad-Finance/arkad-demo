import os
import sys
from pathlib import Path
import streamlit as st
import openai
from langchain.schema import HumanMessage, AIMessage
from langchain_openai.chat_models import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from sql_market_agent.agent.agent import create_sql_market_agent
from langchain_community.callbacks import StreamlitCallbackHandler
from langchain.agents import AgentType
from dotenv import load_dotenv
import json
import traceback
from uuid import uuid4
import logging
from logging.handlers import RotatingFileHandler

# Setup logging to file
log_file = 'streamlit_app.log'

logger = logging.getLogger('streamlit_logger')
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(log_file)
stream_handler = logging.StreamHandler()

log_format = "%(asctime)s - %(levelname)s - %(message)s"
file_handler.setFormatter(logging.Formatter(log_format))
stream_handler.setFormatter(logging.Formatter(log_format))

logger.addHandler(file_handler)
logger.addHandler(stream_handler)


load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB")
DB_USER = os.environ.get("POSTGRES_USER")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
unique_id = uuid4().hex[0:8]
LANGCHAIN_ENDPOINT = os.environ.get("LANGCHAIN_ENDPOINT", "")
if LANGCHAIN_ENDPOINT:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = f"Tracing Walkthrough - {unique_id}"
    os.environ["LANGCHAIN_ENDPOINT"] = os.environ.get("LANGCHAIN_ENDPOINT")
    os.environ["LANGCHAIN_API_KEY"] = os.environ.get("LANGSMITH_API_KEY")


load_dotenv()

openai.api_key = OPENAI_API_KEY

# Create postgres connection string:
db_connection_string = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
# db_connection_string = (
#     f"sqlite:///{Path(__file__).parent / 'StockData.db'}"
# )
if 'agent_executor' not in st.session_state:
    st.session_state["llm"] = ChatOpenAI(temperature=0, 
                                         model="gpt-4-0125-preview", 
                                         streaming=True, 
                                         model_kwargs={"seed": 123})
    st.session_state["sql_llm"] = ChatOpenAI(temperature=0, 
                                             model="gpt-4-0125-preview", 
                                             streaming=True, 
                                             model_kwargs={"seed": 123})
    st.session_state["code_llm"] = ChatOpenAI(temperature=0, 
                                              model="gpt-4-0125-preview", 
                                              streaming=True, 
                                              model_kwargs={"seed": 123})
    st.session_state['agent_executor'] = create_sql_market_agent(
        llm=st.session_state["llm"],
        sql_llm=st.session_state["sql_llm"],
        code_llm=st.session_state["code_llm"],
        agent_type=AgentType.OPENAI_FUNCTIONS,
        preinitialize_database=True,
        db_connection_string=db_connection_string,
        earnings_data_path="./earnings",
        facts_data_path="./facts",
    )


# Predefined prompts
SAVED_SESSIONS = [
    "What was Catterpillar's revenue TTM?",
    "Compare Disney's profit margin with Nvidia's",
    "Tell me latest M&A deals",
]


# Initialize session state for messages if not already present
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        AIMessage(
            content="Welcome! You can ask me anything or select a predefined question."
        )
    ]


def display_chat():
    for msg in st.session_state.messages:
        if isinstance(msg, HumanMessage):
            st.chat_message("user").write(msg.content)
        elif isinstance(msg, AIMessage):
            st.chat_message("assistant").write(msg.content)
            plot_urls = msg.additional_kwargs.get("plot_urls", [])
            for plot_url in plot_urls:
                st.components.v1.iframe(plot_url, width=1500, height=600, scrolling=True)


def handle_response(user_input: str):
    st_callback_answer_container = st.empty()
    st_callback = StreamlitCallbackHandler(st_callback_answer_container)
    try:
        response = st.session_state['agent_executor'](
            {"input": user_input, "chat_history": st.session_state.messages},
            callbacks=[st_callback],
        )
    except Exception as e:
        logger.error(f"Exception occurred when processing users input: {e}")
        traceback.print_exc()
        response = {"output": "There was an error while processing your request :( Please, try with new one."}
    additional_kwargs = {}
    try:
        last_intermediate_step = response['intermediate_steps'][-1]
        last_intermediate_step_output = last_intermediate_step[1]
        last_step_dict = json.loads(last_intermediate_step_output)
        artifacts_paths = last_step_dict.get('artifacts_paths', [])

        # Parsing the JSON string to a Python dictionary
        if artifacts_paths:
            plot_urls = []
            for artifact_path in artifacts_paths:
                artifact = artifact_path.split("/")[-1]
                plot_url = f"http://localhost:8000/{artifact}"
                logger.info(f"Attempting to display HTML file: {artifact} at URL: {plot_url}")
                plot_urls.append(plot_url)
                st.components.v1.iframe(plot_url, width=1500, height=600, scrolling=True)
            additional_kwargs["plot_urls"] = plot_urls
        else:
            logger.info("Artifacts paths not found")
                    
    except IndexError:
        pass
    except Exception as e:
        logger.error("An error occurred: {}".format(e))
        traceback.print_exc()

    response_output = str(response["output"]).replace("$", "\$")
    st.session_state.messages.append(AIMessage(content=response_output, additional_kwargs=additional_kwargs))
    st.write(response_output)


st.set_page_config(page_title="Arkad", layout="wide")

# Predefined prompts selection
with st.form(key="prompt_selection"):
    selected_prompt = st.selectbox(
        "Choose a predefined prompt", options=SAVED_SESSIONS, index=0
    )
    if st.form_submit_button("Submit Predefined Prompt"):
        st.session_state.messages.append(HumanMessage(content=selected_prompt))
        st.chat_message("user").write(selected_prompt)
        handle_response(selected_prompt)

# Display the chat messages
display_chat()

# User input for chat
if user_input := st.chat_input():
    st.session_state.messages.append(HumanMessage(content=user_input))
    st.chat_message("user").write(user_input)
    with st.chat_message("assistant"):
        handle_response(user_input)
