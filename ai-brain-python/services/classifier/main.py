import asyncio
import logging
from common.kafka_config import get_consumer
from common.redis_config import get_redis
from logic import get_classification

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

            session_key = f"session:{customer_id}"
            target_stream = await redis.get(session_key)

            if target_stream:
                target_stream = target_stream.decode()
                logger.info(f"📥 De: {customer_id} -> Sesión activa: {target_stream}")
            else:
                target_stream = get_classification(content)
                await redis.set(session_key, target_stream, ex=1800)
                logger.info(f"📥 De: {customer_id} -> Clasificado: {target_stream}")

            await redis.xadd(target_stream, data)
            
    except Exception as e:
        logger.error(f"Error en el loop del clasificador: {e}")
    finally:
        await consumer.stop()
        await redis.aclose()

if __name__ == "__main__":
    asyncio.run(run_classifier())




