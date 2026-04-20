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
            content = data.get('contenido')
            
            
            target_stream = get_classification(content)
            
            logger.info(f"📥 De: {data['customerId']} -> Intención: {target_stream}")

        
            await redis.xadd(target_stream, data)
            
    except Exception as e:
        logger.error(f"Error en el loop del clasificador: {e}")
    finally:
        await consumer.stop()
        await redis.aclose()

if __name__ == "__main__":
    asyncio.run(run_classifier())




