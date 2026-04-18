import asyncio
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import json
import logging

logger = logging.getLogger(__name__)


async def agente_moustro():
    consumer = AIOKafkaConsumer(
        'chat-queries',
        bootstrap_server='localhost:9092',
        group_id="moustro-group"
    )

    producer = AIOKafkaProducer(bootstrap_servers="localhost:9092")

    await consumer.star()
    await producer.start()

    try:
        async for msg in consumer:
            data = json.loads(msg.value.decode('utf-8'))
            logger.info(f"evento recibido:{data['contenido']}")

            respuesta_texto = f"moustro dice: Recibi tu mensaje '{data['contenido']}'"

            payload = {
                "customerId":data['customerId'],
                "reply": respuesta_texto
            }

            await producer.send_and_wait("chat-response", json.dumps(payload).encode('utf-8'))
            logger.info("respuesta enviada a la cola")
    finally:
        await consumer.stop()
        await producer.stop()

asyncio.run(agente_moustro())