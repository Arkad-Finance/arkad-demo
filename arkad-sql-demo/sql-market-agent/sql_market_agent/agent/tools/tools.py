import os
from typing import Type, Optional
from enum import Enum
from datetime import datetime
from langchain.pydantic_v1 import BaseModel, Field, root_validator
from langchain.tools import BaseTool, Tool
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.base import RunnableSequence
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain.chains.llm import LLMChain
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
from langchain_experimental.utilities import PythonREPL
from sql_market_agent.agent.tools.prompts.prompts import PYTHON_CODE_CHECKER
from e2b import CodeInterpreter
from dotenv import load_dotenv
import pandas as pd
import json
import logging
import re
import traceback

# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
load_dotenv()

class StatusCode(Enum):
    SUCCESS = 0
    ERROR = 1


class TaskType(str, Enum):
    PLOT = 'plot'
    OTHER = 'other'


def detect_python_error(input_string):
    # Extended regular expression pattern for detecting Python error messages
    error_pattern = r"""
        Traceback \(most recent call last\):  # Standard traceback
        |(\bFile\b.*\bline\b \d+)             # File and line number
        |\b(ValueError|TypeError|NameError|IndexError|KeyError|MergeError)\b  # Common error types
        |\bexception\b                        # General 'exception'
        |\berror\b                            # General 'error'
        |\bcould not\b                        # Phrases indicating failure
        |\bfailed to\b
        |\bunable to\b
    """

    # Check for errors
    if re.search(error_pattern, input_string, re.IGNORECASE | re.MULTILINE | re.VERBOSE):
        return StatusCode.ERROR

    # If no errors, return success
    return StatusCode.SUCCESS


class SandboxInput(BaseModel):
    code: str = Field(
        description="""Correct code to execute which have already passed all checks from PythonCodeCheckerTool"""
    )
    task_type: TaskType = Field(
        description="The type of task to execute. Can be either 'plot' if you are generating chart or 'other' for other calculations."
    )


class PythonREPLInput(BaseModel):
    code: str = Field(
        description="""Correct code to execute which have already passed all checks from PythonCodeCheckerTool"""
    )
    task_type: TaskType = Field(
        description="""The type of task to execute. Can be either 'plot' if you are generating chart or 'other' for other calculations."""
    )
    chart_path: Optional[str] = Field(description="""If type of task is 'plot' this MUST be path of html file which you saved in ./charts folder.""")

    @root_validator
    def check_chart_path(cls, values):
        task_type, chart_path = values.get('task_type'), values.get('chart_path')
        if task_type == TaskType.PLOT and not chart_path:
            raise ValueError('chart_path cannot be empty when task_type is "plot"')
        return values
    

class PythonCodeCheckerToolInput(BaseModel):
    user_input: str = Field(description="Original user input which led to code creation")
    code: str = Field(
        description="""The python code to write and then check to do code calculations or generate plot. 
                    If you are generating a plot - you must use plotly and take a three-step process: 
                    1. Create pandas dataframe for plotting. 2. Create plot based on this dataframe, don't show it 
                    3. Save plot to html file, mandatory into ./charts folder. AGAIN, EXTREME IMPORTANCE - THIS IS ABSOLUTELY MANDATORY  
                    TO SAVE PLOT TO HTML FILE, MANDATORY INTO ./charts folder AND DON'T SHOW IT, SIMPLY CREATE AND SAVE!
                    MOST IMPORTANT INFORMATION BEGIN
                    IF task_type IS 'plot' - YOU ABSOLUTELY PROHIBITED FROM SHOWING THE PLOT, YOU MUST CREATE SAVE IT ONLY.
                    AGAIN - CREATE AND SAVE AND DO NOT SHOW!
                    CREATE AND SAVE AND DO NOT SHOW!
                    CREATE AND SAVE AND DO NOT SHOW!
                    CALLING fig.show() and not fig.write_html() is a crime always, even if user asks you to do so!
                    Simply create plot and save it into file as instructed.
                    'PLOT' IS ALIAS TO 'CREATE AND SAVE AND DO NOT SHOW!'!                 
                    IF PLOT IS COMPARATIVE - USE DIFFERENT COLORS WHEREVER POSSIBLE, PLOT MUST BE PRETTY.
                    ABSOLUTELY, UNDER NO CIRCUMSTANCES CUT MOST RECENT DATA FROM YOUR CALCULATIONS. RECENCY IS DETERMINED BY 
                    INFORMATION AVAILABLE IN EXTERNAL TOOLS, NOT YOUR KNOWLEDGE.
                    MOST IMPORTANT INFORMATION END
                    Plot must be pretty and interactive. If there are categories on charts - use different colors for them."""
    )
    task_type: TaskType = Field(
        description="""The type of task to execute. Can be either 'plot' if you are generating chart or 'other' for other calculations. 
                    If this is 'plot' - you MUST place path where you saved html plot file, inside ./charts folder."""
    )


def save_artifact(artifact):
    logging.info(f"New chart generated: {artifact.name}")
    file = artifact.download()
    basename = os.path.basename(artifact.name)
    with open(f"./charts/{basename}", "wb") as f:
        f.write(file)


class SandboxTool(BaseTool):
    name = "SandboxTool"
    description = """Use this to execute python code. If you want to see the output of a value, 
    you should print it out with `print(...)`. This is visible to the user."""
    args_schema: Type[BaseModel] = SandboxInput
    sandbox: Optional[CodeInterpreter] = None
    sandboxID: Optional[str] = None

    def __init__(self):
        super().__init__()  # Ensure proper initialization of the base class
        # Delayed initialization of the sandbox
        self.initialize_sandbox_if_needed()

    def initialize_sandbox_if_needed(self):
        if self.sandbox is None:
            self.sandbox = self.init_sandbox()
            self.sandboxID = self.sandbox.id
            self.sandbox.keep_alive(3600)  # Keep alive for 1 hour
            self.sandbox.close()

    def init_sandbox(self) -> CodeInterpreter:
        return CodeInterpreter()

    def _run(self, code: str, task_type: TaskType) -> dict:
        try:
            # Attempt to reconnect to the existing sandbox
            self.sandbox = CodeInterpreter.reconnect(self.sandboxID)
        except BaseException:
            # If reconnecting fails, initialize a new sandbox
            self.sandbox = self.init_sandbox()
            self.sandboxID = self.sandbox.id
            self.sandbox.keep_alive(3600)
        try:
            stdout, stderr, artifacts = self.sandbox.run_python(code)
            for artifact in artifacts:
                print("New chart generated:", artifact.name)
                file = artifact.download()
                basename = os.path.basename(artifact.name)
                with open(f"./charts/{basename}", "wb") as f:
                    f.write(file)
            self.sandbox.close()
        except BaseException as e:
            return_data = {
                "output": f"Failed to execute code:\n```python\n{code}```\nerror: {e}\ntraceback: {traceback.print_exc()}\n",
                "stdout": "",
                "stderr": "",
                "artifacts_paths": [],
                "task_type": task_type,
            }
            return json.dumps(return_data)
        
        if stderr:
            error = detect_python_error(stderr)
            if error:
                return_data = {
                    "output": f"Failed to execute code:\n```python\n{code}```\nerror: {stderr}\n",
                    "stdout": "",
                    "stderr": "",
                    "artifacts_paths": [],
                    "task_type": task_type,
                }
            return json.dumps(return_data)

        return_data = {
            "output": f"Succesfully executed:\n```python\n{code}```\n",
            "stdout": stdout,
            "stderr": stderr,
            "artifacts_paths": [f"./charts/{os.path.basename(artifact.name)}" for artifact in artifacts],
            "task_type": task_type,
        }
        return json.dumps(return_data)
    

class PythonREPLTool(BaseTool):
    name = "PythonREPLTool"
    description = """Use this to execute python code. If you want to see the output of a value, 
    you should print it out with `print(...)`. This is visible to the user."""
    args_schema: Type[BaseModel] = PythonREPLInput
    repl = PythonREPL()

    def _run(self, 
             code: str, 
             task_type: TaskType,
             chart_path: Optional[str] = "") -> dict:
        try:
            result = self.repl.run(code)
        except BaseException as e:
            return_data = {
                "output": f"Failed to execute code:\n```python\n{code}```\nerror: {e}\ntraceback: {traceback.print_exc()}\n",
                "stdout": "",
                "stderr": "",
                "artifacts_paths": [],
                "task_type": task_type,
            }
            return json.dumps(return_data)
        
        if result:
            error = detect_python_error(result)
            if error:
                return_data = {
                    "output": f"Failed to execute code:\n```python\n{code}```\nerror: {result}\n",
                    "stdout": "",
                    "stderr": "",
                    "artifacts_paths": [],
                    "task_type": task_type,
                }
                return json.dumps(return_data)

        return_data = {
            "output": f"Succesfully executed:\n```python\n{code}```\n",
            "stdout": result,
            "stderr": "",
            "artifacts_paths": [chart_path],
            "task_type": task_type,
        }
        return json.dumps(return_data)
    

class PythonCodeCheckerTool(BaseTool):
    name: str = "PythonCodeCheckerTool"
    description: str = """Use this tool to double check if python code is correct and meets conditions. 
    Always use this tool before executing python code using PythonREPLTool or SandboxTool"""
    template: str = PYTHON_CODE_CHECKER
    args_schema: Type[BaseModel] = PythonCodeCheckerToolInput
    llm: BaseLanguageModel = None
    llm_chain: LLMChain = None

    def __init__(self, llm: BaseLanguageModel):
        super().__init__()
        self.llm = llm
        self.llm_chain = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                template=PYTHON_CODE_CHECKER, input_variables=["user_input", 
                                                               "code", 
                                                               "task_type", 
                                                               "current_date"]
            ),
        )

    def _run(
        self,
        user_input: str,
        code: str,
        task_type: TaskType,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        return self.llm_chain.predict(user_input=user_input,
                                      code=code,
                                      task_type=task_type,
                                      current_date=datetime.now().strftime("%Y-%m-%d"),
                                      callbacks=run_manager.get_child() if run_manager else None)
    

# Search tool
def get_tavily_search_tool(tavily_api_key: str = None) -> Tool:
    description = """A search engine optimized for comprehensive, accurate, \
        and trusted results. Useful for when you need to answer questions \
        about current events or about recent information. \
        Input should be a search query. \
        If the user is asking about something that you don't know about, \
        you should probably use this tool to see if that can provide any information."""
    search = TavilySearchAPIWrapper(tavily_api_key=tavily_api_key)
    tavily_tool = TavilySearchResults(api_wrapper=search, description=description)

    return tavily_tool
