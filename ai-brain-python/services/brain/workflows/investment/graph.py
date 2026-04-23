from langgraph.graph import StateGraph, START, END
from services.brain.workflows.investment.state import InvestmentState
from services.brain.workflows.investment.questionnaire import QUIZ
from services.brain.workflows.investment.nodes import (
    check_profile_node,
    quiz_node,
    persist_profile_node,
    build_advisor_fn,
)
from services.llms.models import get_bedrock_model_brain


def route_after_check(state: InvestmentState) -> str:
    if state.get("has_profile") is True:
        return "advisor"
    return "quiz"


def route_after_quiz(state: InvestmentState) -> str:
    if len(state.get("quiz_answers") or []) >= len(QUIZ):
        return "persist"
    return "quiz"


def build_graph(checkpointer):
    model = get_bedrock_model_brain()
    advisor = build_advisor_fn(model)

    builder = StateGraph(InvestmentState)
    builder.add_node("check_profile", check_profile_node)
    builder.add_node("quiz", quiz_node)
    builder.add_node("persist_profile", persist_profile_node)
    builder.add_node("advisor", advisor)

    builder.add_edge(START, "check_profile")
    builder.add_conditional_edges(
        "check_profile",
        route_after_check,
        {"advisor": "advisor", "quiz": "quiz"},
    )
    builder.add_conditional_edges(
        "quiz",
        route_after_quiz,
        {"persist": "persist_profile", "quiz": "quiz"},
    )
    builder.add_edge("persist_profile", "advisor")
    builder.add_edge("advisor", END)
    return builder.compile(checkpointer=checkpointer)
