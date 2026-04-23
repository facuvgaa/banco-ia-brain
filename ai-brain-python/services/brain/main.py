import asyncio
import logging
from common.kafka_config import ensure_redis_stream_group, xreadgroup_with_recovery
from common.redis_config import get_redis
from services.brain.classifier.logic import (
    BRAIN_WORKFLOW_TTL_S,
    get_brain_classification,
    should_reclassify_brain_workflow,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Límite para no inflar tokens en el router Haiku (último mensaje del asistente).
_MAX_CONTEXTO_BRAIN_CLS = 12_000


async def run_brain():
    redis = get_redis()
    await ensure_redis_stream_group(redis, "to-brain", "brain-group")

    logger.info("Brain activo: to-brain → Haiku elige workflow (loans | investment)…")

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
                if len(contexto) > _MAX_CONTEXTO_BRAIN_CLS:
                    contexto = contexto[:_MAX_CONTEXTO_BRAIN_CLS] + "\n…"

                wf_key = f"brain_workflow:{customer_id}"
                raw_cached = await redis.get(wf_key)
                if raw_cached and not should_reclassify_brain_workflow(
                    raw_cached.decode(), contenido
                ):
                    workflow = raw_cached.decode()
                    logger.info("🔀 %s → %s (caché, sin Haiku)", customer_id, workflow)
                else:
                    workflow = get_brain_classification(
                        contenido, ultimo_asistente=contexto or None
                    )
                    logger.info("🔀 %s → %s", customer_id, workflow)
                await redis.set(wf_key, workflow, ex=BRAIN_WORKFLOW_TTL_S)

                await redis.xadd(workflow,{
                    "customerId": customer_id,
                    "contenido": contenido,
                    "contexto": contexto
                })
                await redis.xack("to-brain", "brain-group", msg_id)

if __name__ == "__main__":
    asyncio.run(run_brain())