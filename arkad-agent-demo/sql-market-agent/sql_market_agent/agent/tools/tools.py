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
from sql_market_agent.agent.tools.prompts.prompts import PYTHON_PROGRAMMER_INSTRUCTIONS
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

TEMP_CSV_PATH = "./artifacts/temp.csv"


class StatusCode(Enum):
    SUCCESS = 0
    ERROR = 1


class TaskType(str, Enum):
    PLOT = "plot"
    OTHER = "other"


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
    if re.search(
        error_pattern, input_string, re.IGNORECASE | re.MULTILINE | re.VERBOSE
    ):
        return StatusCode.ERROR

    # If no errors, return success
    return StatusCode.SUCCESS


class SandboxInput(BaseModel):
    code: str = Field(
        description="""Correct code to execute which have already passed all checks from ProgrammerTool"""
    )
    task_type: TaskType = Field(
        description="The type of task to execute. Can be either 'plot' if you are generating chart or 'other' for other calculations."
    )


class PythonREPLInput(BaseModel):
    code: str = Field(
        description="""Correct code to execute which have already passed all checks from ProgrammerTool. This code must come from ProgrammerTool only, 
        you are strictly prohibited from altering code in any tool other than ProgrammerTool. Again, altering code from ProgrammerTool is strictly prohibited, pay 
        extreme attention """
    )
    task_type: TaskType = Field(
        description="""The type of task to execute. Can be either 'plot' if you are generating chart or 'other' for other calculations."""
    )
    artifact_path: Optional[str] = Field(
        description="""If somewhere in code you create some artifact such as .csv file or chart - include path to that artifact."""
    )

    @root_validator
    def check_chart_path(cls, values):
        task_type, chart_path = values.get("task_type"), values.get("artifact_path")
        if task_type == TaskType.PLOT and not chart_path:
            raise ValueError('chart_path cannot be empty when task_type is "plot"')
        return values


class PythonProgrammerToolInput(BaseModel):
    user_input: str = Field(
        description="Original user input which led to code creation."
    )
    data_path: Optional[str] = Field(
        # description="Path to .csv data file with data pre-fetched to be imported in python code you generate. This field is mandatory if you used "
        # "sql_query_tool to fetch data."
        "./artifacts/temp.csv"
    )
    data_head: Optional[str] = Field(
        description="df.head() of .csv file you will be importing if 'data_path' field is not empty. This field is mandatory if you used "
        "sql_query_tool to fetch data. Carefully look at what columns are available for you."
    )
    code: str = Field(
        description="""The python code you must write and then check to do code calculations or generate plot. 
        When writing python code it MUST satisfy following conditions, complementary to previous instructions: 
        1. If somewhere in code you create some artifact such as .csv file or chart: artifact must be saved in {artifacts_directory}. 
        Code MUST save a plot in html format. 
        2. If task_type is "plot" - code MUST NOT show a plot. 
        3. If task_type is "plot" and user asks to plot comparative chart - code MUST use different colors for different categories. 
        Note, that Plotly does not automatically assign different colors to different traces (categories) in a grouped bar chart. 
        Code MUST handle this color rule explicitly, which means that it MUST explicitly set colors in code, other approaches are strictly prohibited. 
        3. If task_type is "plot" - do your best to use best possible x-axis and y-axis lables to describe what is plotted. 
        4. If task_type is "plot" - data MUST be correctly displayed on chart and easily readable for user.  
        5. If 'data_path' field is not empty - you must import data from that path into pandas DataFrame, this is data prefetched for you for further work. 
        Important: 'data_path' that you receive here must be followed strictly without any altering. 
        6. Hardcoding data is absolutely prohibited unless explicitly asked otherwise. 
        """
    )
    previous_code: Optional[str] = Field(
        description="If previous code execution resulted in an error"
    )
    error: Optional[str] = Field(
        description="Actual error if previous code execution resulted in an error"
    )
    task_type: TaskType = Field(
        description="""The type of task to execute. Can be either 'plot' if you are generating chart or 'other' for other calculations. 
                    If this is 'plot' - you MUST place path where you saved html plot file, inside ./artifacts folder."""
    )


class SandboxTool(BaseTool):
    name = "SandboxTool"
    description = """Execute python code. If an error is returned, rewrite the code, check the code, and try again."""
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
                print("New artifact generated:", artifact.name)
                file = artifact.download()
                basename = os.path.basename(artifact.name)
                with open(f"./artifacts/{basename}", "wb") as f:
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
            "artifacts_paths": [
                f"./artifacts/{os.path.basename(artifact.name)}"
                for artifact in artifacts
            ],
            "task_type": task_type,
        }
        return json.dumps(return_data)


class PythonREPLTool(BaseTool):
    name = "PythonREPLTool"
    description = """Execute python code. If an error is returned, rewrite the code using ProgrammerTool, check the code, and try again."""
    args_schema: Type[BaseModel] = PythonREPLInput
    repl = PythonREPL()

    def _run(
        self, code: str, task_type: TaskType, artifact_path: Optional[str] = ""
    ) -> dict:
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
            "artifacts_paths": [artifact_path],
            "task_type": task_type,
        }
        return json.dumps(return_data)


class PythonProgrammerTool(BaseTool):
    name: str = "ProgrammerTool"
    description: str = """Use this tool to write python code and to double check if python code is correct and meets conditions. 
    Always use this tool before executing python code using PythonREPLTool or SandboxTool"""
    template: str = PYTHON_PROGRAMMER_INSTRUCTIONS
    args_schema: Type[BaseModel] = PythonProgrammerToolInput
    llm: BaseLanguageModel = None
    llm_chain: LLMChain = None
    artifacts_directory: str = None

    def __init__(self, llm: BaseLanguageModel, artifacts_directory: str):
        super().__init__()
        code_description = self.args_schema.__fields__["code"].field_info.description
        updated_description = code_description.format(
            artifacts_directory=artifacts_directory
        )
        self.args_schema.__fields__["code"].field_info.description = updated_description
        self.llm = llm
        self.llm_chain = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                template=self.template,
                input_variables=[
                    "user_input",
                    "data_head",
                    "code",
                    "previous_code",
                    "error",
                    "task_type",
                    "current_date",
                ],
            ).partial(data_path=TEMP_CSV_PATH, artifacts_directory=artifacts_directory),
        )

    def _run(
        self,
        user_input: str,
        code: str,
        task_type: TaskType,
        data_path: Optional[str] = "",
        data_head: Optional[str] = "",
        previous_code: Optional[str] = "",
        error: Optional[str] = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        return self.llm_chain.predict(
            user_input=user_input,
            data_path=data_path,
            data_head=data_head,
            code=code,
            previous_code=previous_code,
            error=error,
            task_type=task_type,
            current_date=datetime.now().strftime("%Y-%m-%d"),
            callbacks=run_manager.get_child() if run_manager else None,
        )


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
