import json
import logging
import os

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from dotenv import load_dotenv
from redis.exceptions import ResponseError

load_dotenv()

logger = logging.getLogger(__name__)

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BROKER", "localhost:9092")


def get_producer() -> AIOKafkaProducer:
    # Sin value_serializer: el payload a chat-response es siempre bytes JSON (ver send_chat_response).
    return AIOKafkaProducer(bootstrap_servers=BOOTSTRAP_SERVERS)


async def send_chat_response(producer: AIOKafkaProducer, customer_id: str, reply: str) -> None:
    """Publica en chat-response el JSON que consume Java (String + ObjectMapper)."""
    raw = json.dumps(
        {"customerId": customer_id, "reply": reply},
        ensure_ascii=False,
    ).encode("utf-8")
    await producer.send_and_wait("chat-response", raw)
    logger.info(
        "Kafka chat-response publicado customerId=%s chars=%s",
        customer_id,
        len(reply) if reply else 0,
    )


def get_consumer(topic, group_id):
    return AIOKafkaConsumer(
        topic,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=group_id,
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    )


async def ensure_redis_stream_group(redis, stream: str, group: str) -> None:
    """Crea stream + consumer group si no existen (evita NOGROUP en xreadgroup)."""
    try:
        await redis.xgroup_create(stream, group, id="0", mkstream=True)
        logger.info("Redis: stream %s grupo %s creados", stream, group)
        return
    except ResponseError as e:
        msg = str(e)
        if "BUSYGROUP" in msg or "busygroup" in msg.lower():
            return
        # Stream puede existir solo por XADD (sin grupo); crear el grupo sobre el stream
        try:
            await redis.xgroup_create(stream, group, id="0", mkstream=False)
            logger.info(
                "Redis: grupo %s creado sobre stream ya existente %s", group, stream
            )
            return
        except ResponseError as e2:
            msg2 = str(e2)
            if "BUSYGROUP" in msg2 or "busygroup" in msg2.lower():
                return
            raise e2 from e


async def xreadgroup_with_recovery(
    redis,
    stream: str,
    group: str,
    consumer: str,
    *,
    count: int = 1,
    block: int = 1000,
):
    """
    XREADGROUP con reintento si Redis se vació (FLUSHALL), falta stream/grupo,
    o el stream existía sin grupo (solo XADD).
    """
    streams = {stream: ">"}
    for attempt in range(3):
        try:
            return await redis.xreadgroup(
                group, consumer, streams, count=count, block=block
            )
        except Exception as e:
            # ResponseError/RedisError a veces llegan distinto según versión; matchear por texto
            err = str(e).lower()
            recoverable = (
                "nogroup" in err
                or "no such key" in err
                or "consumer group" in err
            )
            if recoverable and attempt < 2:
                logger.warning(
                    "Redis: xreadgroup falló, reasegurando stream=%s group=%s: %s",
                    stream,
                    group,
                    e,
                )
                await ensure_redis_stream_group(redis, stream, group)
                continue
            raise
