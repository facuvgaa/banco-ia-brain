import asyncio
import logging

from common.kafka_config import get_consumer, get_producer, send_chat_response
from common.redis_config import get_redis
from services.classifier.logic import get_classification
from services.classifier.post_close_logic import get_post_close_route

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Respuesta mínima si el usuario cierra luego de “¿algo más?”.
POST_CLOSE_FAREWELL = (
    "Dale, cuando quieras. ¡Gracias por charlar y que tengas un buen día!"
)


async def run_classifier():
    consumer = get_consumer("chat-queries", "classifier-group")
    redis = get_redis()
    producer = get_producer()
    await consumer.start()
    await producer.start()

    logger.info("🚀 Clasificador Moustro (Haiku) + post-cierre en chat-queries...")

    try:
        async for msg in consumer:
            data = msg.value
            customer_id = data.get("customerId")
            content = data.get("contenido")

            session_key = f"session:{customer_id}"
            post_close_key = f"post_close:{customer_id}"

            if await redis.get(post_close_key):
                action = get_post_close_route(content or "")
                await redis.delete(post_close_key)
                if action == "close":
                    await redis.delete(session_key)
                    await send_chat_response(producer, customer_id, POST_CLOSE_FAREWELL)
                    logger.info("📤 post_close → CERRAR %s (sin reenvío)", customer_id)
                    continue
                await redis.delete(session_key)
                logger.info("📤 post_close → NUEVO tema %s (reclasificando)", customer_id)

            # Sin sesión: Haiku + guardar ruta. Con sesión: misma vía (sin reclasificar).
            # Forzar reclasificar: `DEL session:<customerId>`.
            cached = await redis.get(session_key)

            if cached:
                target_stream = cached.decode()
                logger.info("📥 De: %s -> sesión: %s", customer_id, target_stream)
            else:
                target_stream = get_classification(content)
                await redis.set(session_key, target_stream, ex=1800)
                logger.info("📥 De: %s -> Haiku: %s", customer_id, target_stream)

            fields = {k: str(v) if v is not None else "" for k, v in data.items()}
            await redis.xadd(target_stream, fields)

    except Exception as e:
        logger.error("Error en el loop del clasificador: %s", e)
    finally:
        await consumer.stop()
        await producer.stop()
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(run_classifier())
