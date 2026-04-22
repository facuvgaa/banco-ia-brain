from functools import partial
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from llms.models import get_bedrock_model_brain
from workflows.loans.state import LoanState
from workflows.loans.tools import DESTRUCTIVE_TOOLS, DESTRUCTIVE_TOOL_NAMES
from workflows.loans.nodes import load_data_node, agent_node, confirmation_node


def route_after_agent(state: LoanState) -> str:
    last = state["messages"][-1]
    if not getattr(last, "tool_calls", None):
        return END
    tool_name = last.tool_calls[0]["name"]
    return "confirm" if tool_name in DESTRUCTIVE_TOOL_NAMES else "tools"


def route_after_confirm(state: LoanState) -> str:
    return "tools" if state.get("confirmed") else END


def build_graph(checkpointer):
    model = get_bedrock_model_brain().bind_tools(DESTRUCTIVE_TOOLS)

    builder = StateGraph(LoanState)

    builder.add_node("load_data", load_data_node)
    builder.add_node("agent", partial(agent_node, model=model))
    builder.add_node("confirm", confirmation_node)
    builder.add_node("tools", ToolNode(DESTRUCTIVE_TOOLS))

    builder.add_edge(START, "load_data")
    builder.add_edge("load_data", "agent")
    builder.add_conditional_edges("agent", route_after_agent, {
        "confirm": "confirm",
        "tools": "tools",
        END: END,
    })
    builder.add_conditional_edges("confirm", route_after_confirm, {
        "tools": "tools",
        END: END,
    })
    builder.add_edge("tools", "agent")

    return builder.compile(checkpointer=checkpointer)
