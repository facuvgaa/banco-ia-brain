from __future__ import annotations

from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, MessagesState, StateGraph

from services.llms.models import get_bedrock_model_master
from services.master.prompt import SYSTEM_PROMPT

model = get_bedrock_model_master()


def _nombre_corto_from_thread_id(thread_id: str) -> str:
    t = (thread_id or "").lower().strip()
    if not t:
        return "cliente"
    if "facuvega" in t or t.startswith("facu"):
        return "Facu"
    base = t.split("-")[0].split("_")[0]
    if not base:
        return "cliente"
    return base[0].upper() + base[1:].lower()


async def agent_node(state: MessagesState, *, config: RunnableConfig) -> dict:
    conf = config.get("configurable") or {}
    thread_id = conf.get("thread_id", "cliente")
    nombre = _nombre_corto_from_thread_id(str(thread_id))
    system = SystemMessage(content=SYSTEM_PROMPT.format(nombre_corto=nombre))
    messages = [system] + state["messages"]
    response = await model.ainvoke(messages)
    return {"messages": [response]}


def build_graph():
    builder = StateGraph(MessagesState)
    builder.add_node("agent", agent_node)
    builder.add_edge(START, "agent")
    builder.add_edge("agent", END)
    return builder
