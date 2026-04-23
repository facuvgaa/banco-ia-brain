import asyncio
import logging
import os
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.redis import AsyncRedisSaver
from common.redis_config import get_redis
from common.post_close_kafka import send_reply_set_post_close_if_marker
from common.kafka_config import (
    get_producer,
    send_chat_response,
    ensure_redis_stream_group,
    xreadgroup_with_recovery,
)
from common.conversation_store import init_db, save_conversation
from services.master.graph import build_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


def _text_from_message_content(content) -> str:
    """Converse (Bedrock) a veces devuelve str o lista de bloques; unificamos a str."""
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


async def run_master():
    await init_db()

    redis = get_redis()
    await ensure_redis_stream_group(redis, "to-master", "master-group")
    producer = get_producer()
    await producer.start()

    async with AsyncRedisSaver.from_conn_string(REDIS_URL) as checkpointer:
        graph = build_graph().compile(checkpointer=checkpointer)

        logger.info("🧠 Master activo en stream:to-master...")

        while True:
            results = await xreadgroup_with_recovery(
                redis,
                "to-master",
                "master-group",
                "worker-1",
                count=1,
                block=1000,
            )

            if not results:
                continue

            for _, messages in results:
                for msg_id, data in messages:
                    customer_id = "unknown"
                    try:
                        customer_id = data[b"customerId"].decode().strip()
                        contenido = data[b"contenido"].decode()
                        config = {"configurable": {"thread_id": customer_id}}

                        result = await graph.ainvoke(
                            {"messages": [HumanMessage(content=contenido)]},
                            config=config,
                        )
                        raw = result["messages"][-1].content
                        respuesta = _text_from_message_content(raw)

                        if "[DERIVAR]" in respuesta:
                            await redis.delete(f"brain_workflow:{customer_id}")
                            await redis.set(
                                f"session:{customer_id}", "to-brain", ex=1800
                            )
                            await redis.xadd(
                                "to-brain",
                                {
                                    "customerId": customer_id,
                                    "contenido": contenido,
                                    "contexto": respuesta.replace(
                                        "[DERIVAR]", ""
                                    ).strip(),
                                },
                            )
                            logger.info("➡️ Derivando %s a brain", customer_id)
                        else:
                            await send_reply_set_post_close_if_marker(
                                redis, producer, customer_id, respuesta
                            )
                            try:
                                await save_conversation(
                                    customer_id, "master", result["messages"]
                                )
                            except Exception:
                                logger.exception(
                                    "save_conversation falló (la respuesta ya se envió)"
                                )
                    except Exception:
                        logger.exception("Error en master para %s", customer_id)
                        try:
                            await send_chat_response(
                                producer,
                                customer_id,
                                "Tuvimos un error al generar la respuesta. Probá de nuevo en un rato.",
                            )
                        except Exception:
                            logger.exception(
                                "No se pudo publicar error a chat-response"
                            )
                    finally:
                        await redis.xack("to-master", "master-group", msg_id)


if __name__ == "__main__":
    asyncio.run(run_master())