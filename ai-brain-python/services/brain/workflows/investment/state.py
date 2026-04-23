from typing import Annotated, NotRequired, Optional, TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class InvestmentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    customer_id: str
    has_profile: NotRequired[Optional[bool]]
    investor_tier: NotRequired[Optional[str]]
    quiz_answers: NotRequired[list[str]]
    quiz_total_score: NotRequired[Optional[int]]
    max_loss_percent: NotRequired[Optional[int]]
    horizon: NotRequired[Optional[str]]
    profile_persisted: NotRequired[bool]
