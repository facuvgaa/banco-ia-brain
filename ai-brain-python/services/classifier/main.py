import asyncio
import logging
from common.kafka_config import get_consumer, get_producer
from logic import get_classification # Tu lógica con Haiku

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_classifier():
    
    
    consumer = get_consumer('chat-queries', 'classifier-group')
    producer = get_producer()

    await consumer.start()
    await producer.start()

    logger.info("🚀 Clasificador Moustro (Haiku) activo en chat-queries...")

    try:
        async for msg in consumer:
            data = msg.value
            content = data.get('contenido')
            
            
            target_topic = get_classification(content)
            
            logger.info(f"📥 De: {data['customerId']} -> Intención: {target_topic}")

        
            await producer.send_and_wait(target_topic, data)
            
    except Exception as e:
        logger.error(f"Error en el loop del clasificador: {e}")
    finally:
        await consumer.stop()
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(run_classifier())




