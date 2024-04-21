from datetime import datetime, timedelta
from dateutil import parser, relativedelta
from langchain.tools import tool
from pydantic.v1 import BaseModel, Field
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool
from typing import Type
import re


def weekday_to_relativedelta(weekday: str):
    weekdays = {
        "monday": relativedelta.MO,
        "tuesday": relativedelta.TU,
        "wednesday": relativedelta.WE,
        "thursday": relativedelta.TH,
        "friday": relativedelta.FR,
        "saturday": relativedelta.SA,
        "sunday": relativedelta.SU,
    }
    return weekdays.get(weekday.lower())


class Query(BaseModel):
    query: str = Field(..., description="Some date reference to convert to exact date.")


class DateTool(BaseTool):
    name = "date_tool"
    description = """Useful when you need to get an exact date for some query.
        You must use DateTool to get appropriate date representation for any subsequent tools
        which require date as input."""
    args_schema: Type[BaseModel] = Query

    def _run(self, query: str) -> str:
        today = datetime.now()
        query = query.lower()

        # Find the weekday in the query, if present
        match = re.search(
            r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", query
        )
        weekday = match.group(0) if match else None

        if query == "today":
            return today.strftime("%Y-%m-%d")
        elif query == "yesterday":
            return (today - timedelta(days=1)).strftime("%Y-%m-%d")
        elif query == "tomorrow":
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")
        elif weekday:
            rd_weekday = weekday_to_relativedelta(weekday)
            if rd_weekday:
                if query == weekday:
                    # For just "<weekday>", find the most recent past instance
                    return (
                        today - relativedelta.relativedelta(weekday=rd_weekday(-1))
                    ).strftime("%Y-%m-%d")
                elif "last week" in query:
                    # For "<weekday> last week"
                    return (
                        today
                        - relativedelta.relativedelta(weeks=1, weekday=rd_weekday(-1))
                    ).strftime("%Y-%m-%d")
                elif "week ago" in query:
                    # For "<weekday> last week"
                    return (
                        today
                        - relativedelta.relativedelta(weeks=1, weekday=rd_weekday(-1))
                    ).strftime("%Y-%m-%d")
                elif "two weeks ago" in query:
                    # For "<weekday> two weeks ago"
                    return (
                        today
                        - relativedelta.relativedelta(weeks=2, weekday=rd_weekday(-1))
                    ).strftime("%Y-%m-%d")
                elif "second to last" in query:
                    # For "second to last <weekday>"
                    return (
                        today
                        - relativedelta.relativedelta(weeks=2, weekday=rd_weekday(-1))
                    ).strftime("%Y-%m-%d")
                elif "second to next" in query:
                    # For "second to next <weekday>"
                    return (
                        today
                        + relativedelta.relativedelta(weeks=1, weekday=rd_weekday(+1))
                    ).strftime("%Y-%m-%d")
                elif "last" in query:
                    # For "last <weekday>", ensuring it's not this week
                    return (
                        (
                            today - relativedelta.relativedelta(weekday=rd_weekday(-1))
                        ).strftime("%Y-%m-%d")
                        if today.weekday() != rd_weekday.weekday
                        else (
                            today
                            - relativedelta.relativedelta(
                                weeks=1, weekday=rd_weekday(-1)
                            )
                        ).strftime("%Y-%m-%d")
                    )
                elif "next" in query:
                    # For "next <weekday>"
                    return (
                        today + relativedelta.relativedelta(weekday=rd_weekday(+1))
                    ).strftime("%Y-%m-%d")
            else:
                return "Invalid weekday"
        else:
            # For other types of dates, try to parse directly
            try:
                return parser.parse(query).strftime("%Y-%m-%d")
            except ValueError:
                return "I could not parse date"
