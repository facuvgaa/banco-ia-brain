import logging

from common.post_close import POST_CLOSE_TTL_S, strip_post_close_marker
from common.kafka_config import send_chat_response

logger = logging.getLogger(__name__)


async def send_reply_set_post_close_if_marker(redis, producer, customer_id: str, text: str) -> None:
    """
    Publica en chat-response; si el texto trae [POST_CLOSE], quita el marcador
    y setea post_close:{customerId} con TTL acotado.
    """
    clean, is_pc = strip_post_close_marker(text)
    if is_pc:
        key = f"post_close:{customer_id}"
        await redis.set(key, "1", ex=POST_CLOSE_TTL_S)
        logger.info("post_close set customerId=%s", customer_id)
    await send_chat_response(producer, customer_id, clean)
