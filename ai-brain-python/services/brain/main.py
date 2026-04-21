import asyncio
import logging
from common.redis_config import get_redis
from classifier.logic import get_brain_classification



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_brain():
    redis = get_redis()

    logger.info("Brain clasificador activo en stream: to-brain")

    while True:
        results = await redis.xreadgroup(
            "brain_group", "worker-1",
            {"to-brain": ">"},
            count=1, block=1000
        )

        if not results:
            continue

        for _, messages in results:
            for msg_id, data in messages:
                customer_id = data[b"customerId"].decode()
                contenido = data[b"contenido"].decode()
                contexto = data.get(b"contexto", b"").decode()

                workflow = get_brain_classification(contenido)
                

                logger.info(f"🔀 {customer_id} → {workflow}")

                await redis.xadd(workflow,{
                    "customerId": customer_id,
                    "contenido": contenido,
                    "contexto": contexto
                })
                await redis.xack("to-brain", "brain-group", msg_id)

if __name__ == "__main__":
    asyncio.run(run_brain())