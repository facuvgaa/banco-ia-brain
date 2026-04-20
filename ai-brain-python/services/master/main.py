import asyncio
import logging
import json
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.redis import AsyncRedisSaver
from common.redis_config import get_redis
from common.kafka_config import get_producer
from graph import build_graph
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

async def run_master():
    redis = get_redis()
    producer = get_producer()
    await producer.start()

    async with AsyncRedisSaver.from_conn_string(REDIS_URL) as checkpointer:
        graph = build_graph().compile(checkpointer=checkpointer)

        logger.info("🧠 Master activo en stream:to-master...")

        while True:
            results = await redis.xreadgroup(
                "master-group", "worker-1",
                {"to-master": ">"},
                count=1, block=1000
            )

            if not results:
                continue

            for _, messages in results:
                for msg_id, data in messages:
                    customer_id = data[b"customerId"].decode()
                    contenido = data[b"contenido"].decode()

                    config = {"configurable": {"thread_id": customer_id}}

                    result = await graph.ainvoke(
                        {"messages": [HumanMessage(content=contenido)]},
                        config=config
                    )

                    respuesta = result["messages"][-1].content

                    # Si master detecta que hay que derivar a brain
                    if "[DERIVAR]" in respuesta:
                        await redis.set(f"session:{customer_id}", "to-brain", ex=1800)
                        await redis.xadd("to-brain", {
                            "customerId": customer_id,
                            "contenido": contenido,
                            "contexto": respuesta.replace("[DERIVAR]", "").strip()
                        })
                        logger.info(f"➡️ Derivando {customer_id} a brain")
                    else:
                        await producer.send_and_wait(
                            "chat-response",
                            json.dumps({"customerId": customer_id, "reply": respuesta}).encode()
                        )

                    await redis.xack("to-master", "master-group", msg_id)

if __name__ == "__main__":
    asyncio.run(run_master())