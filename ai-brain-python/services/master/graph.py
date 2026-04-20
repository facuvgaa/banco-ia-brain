from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_core.messages import SystemMessage
from llms.models import get_bedrock_model_master
from prompt import SYSTEM_PROMPT

model = get_bedrock_model_master()

async def agent_node(state: MessagesState):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = await model.ainvoke(messages)
    return {"messages": [response]}


def build_graph():
    builder = StateGraph(MessagesState)
    builder.add_node("agent", agent_node)
    builder.add_edge(START, "agent")
    builder.add_edge("agent", END)
    return builder
