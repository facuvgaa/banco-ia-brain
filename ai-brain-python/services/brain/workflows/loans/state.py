from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class LoanState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    customer_id: str
    loans: list
    refinanceable: list
    offers: list
    confirmed: bool
