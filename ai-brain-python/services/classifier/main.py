import asyncio
import logging
from common.kafka_config import get_consumer
from common.redis_config import get_redis
from services.classifier.logic import get_classification

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_classifier():
    consumer = get_consumer('chat-queries', 'classifier-group')
    redis = get_redis()

    await consumer.start()

    logger.info("🚀 Clasificador Moustro (Haiku) activo en chat-queries...")

    try:
        async for msg in consumer:
            data = msg.value
            customer_id = data.get('customerId')
            content = data.get('contenido')

            # Sin sesión: Haiku + guardar ruta. Con sesión: misma vía (sin reclasificar).
            # Forzar reclasificar: `DEL session:<customerId>`.
            session_key = f"session:{customer_id}"
            cached = await redis.get(session_key)

            if cached:
                target_stream = cached.decode()
                logger.info(f"📥 De: {customer_id} -> sesión: {target_stream}")
            else:
                target_stream = get_classification(content)
                await redis.set(session_key, target_stream, ex=1800)
                logger.info(f"📥 De: {customer_id} -> Haiku: {target_stream}")

            fields = {k: str(v) if v is not None else "" for k, v in data.items()}
            await redis.xadd(target_stream, fields)
            
    except Exception as e:
        logger.error(f"Error en el loop del clasificador: {e}")
    finally:
        await consumer.stop()
        await redis.aclose()

if __name__ == "__main__":
    asyncio.run(run_classifier())




