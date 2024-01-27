import os
import streamlit as st
import openai
from langchain.schema import HumanMessage, AIMessage
from langchain_openai.chat_models import ChatOpenAI
from pandas_market_agent.agent.agent import create_pandas_market_agent
from langchain_community.callbacks import StreamlitCallbackHandler
from dotenv import load_dotenv
import logging

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Setup basic logging
# Configure logging to file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Test log message
logging.info("Started streamlit server...")

load_dotenv()

openai.api_key = OPENAI_API_KEY

st.set_page_config(page_title="Arkad", layout="wide")


llm = ChatOpenAI(
    temperature=0,
    model="gpt-4",
    streaming=True,
)

agent_executor = create_pandas_market_agent(
    llm=llm,
    stocks=["CAT", "NKE", "XOM"],
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
        else:
            st.chat_message("assistant").write(msg.content)


# Predefined prompts selection
with st.form(key="prompt_selection"):
    selected_prompt = st.selectbox(
        "Choose a predefined prompt", options=SAVED_SESSIONS, index=0
    )
    if st.form_submit_button("Submit Predefined Prompt"):
        st.session_state.messages.append(HumanMessage(content=selected_prompt))
        st_callback_answer_container = st.empty()
        st_callback = StreamlitCallbackHandler(st_callback_answer_container)
        response = agent_executor(
            {"input": selected_prompt, "chat_history": st.session_state.messages},
            callbacks=[st_callback],
        )
        st.session_state.messages.append(AIMessage(content=response["output"]))
        st.write(response["output"])

# Display the chat messages
display_chat()

# User input for chat
if user_input := st.chat_input():
    st.session_state.messages.append(HumanMessage(content=user_input))
    st.chat_message("user").write(user_input)
    with st.chat_message("assistant"):
        st_callback_answer_container = st.empty()
        st_callback = StreamlitCallbackHandler(st_callback_answer_container)
        response = agent_executor(
            {"input": user_input, "chat_history": st.session_state.messages},
            callbacks=[st_callback],
        )
        response = str(response["output"]).replace("$", "\$")
        st.session_state.messages.append(AIMessage(content=response))
        st.write(response)
