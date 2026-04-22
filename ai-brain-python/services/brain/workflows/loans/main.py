import asyncio
import logging
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from common.redis_config import get_redis, get_checkpointer
from common.kafka_config import (
    get_producer,
    send_chat_response,
    ensure_redis_stream_group,
    xreadgroup_with_recovery,
)
from common.conversation_store import init_db, save_conversation
from services.brain.workflows.loans.graph import build_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _text_from_message_content(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "\n".join(p for p in parts if p) if parts else str(content)
    return str(content)


def _state_from_graph_result(result):
    if hasattr(result, "value"):
        return result.value
    return result


def _interrupts_from_graph_result(result):
    if hasattr(result, "interrupts") and result.interrupts:
        return result.interrupts
    if isinstance(result, dict) and "__interrupt__" in result and result["__interrupt__"]:
        return result["__interrupt__"]
    return ()


async def run():
    await init_db()

    redis = get_redis()
    await ensure_redis_stream_group(redis, "workflow_loans", "loans-group")
    producer = get_producer()
    await producer.start()

    async with get_checkpointer() as checkpointer:
        graph = build_graph(checkpointer)

        logger.info("💳 Workflow Préstamos activo en stream:workflow_loans...")

        while True:
            results = await xreadgroup_with_recovery(
                redis,
                "workflow_loans",
                "loans-group",
                "worker-1",
                count=1,
                block=1000,
            )

            if not results:
                continue

            for _, messages in results:
                for msg_id, data in messages:
                    customer_id = data[b"customerId"].decode()
                    contenido = data[b"contenido"].decode()
                    contexto = data.get(b"contexto", b"").decode()

                    config = {"configurable": {"thread_id": customer_id}}

                    initial_messages = []
                    if contexto:
                        initial_messages.append(HumanMessage(content=f"Contexto previo: {contexto}"))
                    initial_messages.append(HumanMessage(content=contenido))

                    try:
                        try:
                            snap = await graph.aget_state(config)
                            waiting_confirm = bool(snap.interrupts)
                        except Exception as ex:
                            logger.debug("[loans] aget_state: %s", ex)
                            waiting_confirm = False

                        if waiting_confirm:
                            result = await graph.ainvoke(
                                Command(resume=contenido), config=config
                            )
                        else:
                            result = await graph.ainvoke(
                                {
                                    "messages": initial_messages,
                                    "customer_id": customer_id,
                                    "loans": [],
                                    "refinanceable": [],
                                    "offers": [],
                                    "confirmed": False,
                                },
                                config=config,
                            )

                        intrs = _interrupts_from_graph_result(result)
                        state = _state_from_graph_result(result)

                        if intrs:
                            first = intrs[0]
                            pregunta = (
                                first.value
                                if hasattr(first, "value")
                                else getattr(first, "value", first)
                            )
                            await send_chat_response(
                                producer, customer_id, str(pregunta)
                            )
                        elif isinstance(state, dict) and state.get("messages"):
                            raw = state["messages"][-1].content
                            text = _text_from_message_content(raw)
                            await send_chat_response(producer, customer_id, text)
                            try:
                                await save_conversation(
                                    customer_id, "loans", state["messages"]
                                )
                            except Exception:
                                logger.exception(
                                    "save_conversation (loans) falló; respuesta ya enviada"
                                )
                        else:
                            logger.warning(
                                "[loans] Sin mensaje ni interrupt para %s", customer_id
                            )
                            await send_chat_response(
                                producer,
                                customer_id,
                                "No se pudo generar la respuesta de préstamos. Probá de nuevo.",
                            )

                    except Exception as e:
                        logger.exception("[loans] Error procesando %s", customer_id)
                        try:
                            await send_chat_response(
                                producer,
                                customer_id,
                                "Tuvimos un error al armar la respuesta de préstamos. Probá de nuevo.",
                            )
                        except Exception:
                            pass

                    await redis.xack("workflow_loans", "loans-group", msg_id)


async def resume(customer_id: str, respuesta_usuario: str):
    """Reanuda el graph después de una confirmación del usuario."""
    redis = get_redis()
    producer = get_producer()
    await producer.start()

    async with get_checkpointer() as checkpointer:
        graph = build_graph(checkpointer)
        config = {"configurable": {"thread_id": customer_id}}

        result = await graph.ainvoke(
            Command(resume=respuesta_usuario),
            config=config,
        )
        state = _state_from_graph_result(result)
        raw = state["messages"][-1].content if isinstance(state, dict) else ""
        await send_chat_response(
            producer, customer_id, _text_from_message_content(raw)
        )
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(run())
