import asyncio
import logging
from common.kafka_config import ensure_redis_stream_group, xreadgroup_with_recovery
from common.redis_config import get_redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Único workflow desplegado: préstamos. Cuando existan más, reactivar Haiku en classifier.
WORKFLOW_ACTIVO = "workflow_loans"


async def run_brain():
    redis = get_redis()
    await ensure_redis_stream_group(redis, "to-brain", "brain-group")

    logger.info(
        "Brain activo en stream to-brain → siempre %s (único workflow en esta demo)",
        WORKFLOW_ACTIVO,
    )

    while True:
        results = await xreadgroup_with_recovery(
            redis,
            "to-brain",
            "brain-group",
            "worker-1",
            count=1,
            block=1000,
        )

        if not results:
            continue

        for _, messages in results:
            for msg_id, data in messages:
                customer_id = data[b"customerId"].decode()
                contenido = data[b"contenido"].decode()
                contexto = data.get(b"contexto", b"").decode()

                workflow = WORKFLOW_ACTIVO
                logger.info("🔀 %s → %s", customer_id, workflow)

                await redis.xadd(workflow,{
                    "customerId": customer_id,
                    "contenido": contenido,
                    "contexto": contexto
                })
                await redis.xack("to-brain", "brain-group", msg_id)

if __name__ == "__main__":
    asyncio.run(run_brain())