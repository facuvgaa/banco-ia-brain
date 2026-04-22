import asyncio
import json
import logging
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from common.redis_config import get_redis, get_checkpointer
from common.kafka_config import get_producer
from workflows.loans.graph import build_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run():
    redis = get_redis()
    producer = get_producer()
    await producer.start()

    async with get_checkpointer() as checkpointer:
        graph = build_graph(checkpointer)

        logger.info("💳 Workflow Préstamos activo en stream:workflow_loans...")

        while True:
            results = await redis.xreadgroup(
                "loans-group", "worker-1",
                {"workflow_loans": ">"},
                count=1, block=1000
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

                        # Si el graph se interrumpió esperando confirmación
                        if "__interrupt__" in result:
                            pregunta = result["__interrupt__"][0].value
                            await producer.send_and_wait(
                                "chat-response",
                                json.dumps({"customerId": customer_id, "reply": pregunta}).encode()
                            )
                        else:
                            respuesta = result["messages"][-1].content
                            await producer.send_and_wait(
                                "chat-response",
                                json.dumps({"customerId": customer_id, "reply": respuesta}).encode()
                            )

                    except Exception as e:
                        logger.error(f"[loans] Error procesando {customer_id}: {e}")

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

        respuesta = result["messages"][-1].content
        await producer.send_and_wait(
            "chat-response",
            json.dumps({"customerId": customer_id, "reply": respuesta}).encode()
        )
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(run())
