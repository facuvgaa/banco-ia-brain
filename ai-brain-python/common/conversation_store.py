import os
import json
import logging
import asyncpg
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

POSTGRES_URL = os.getenv("POSTGRES_CONVERSATION_URL", "postgresql://admin:password@localhost:5433/banco_db")

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id          SERIAL PRIMARY KEY,
    customer_id VARCHAR(255) NOT NULL,
    service     VARCHAR(100) NOT NULL,
    messages    JSONB        NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_conversations_customer_id ON conversations(customer_id);
"""


async def _get_connection():
    return await asyncpg.connect(POSTGRES_URL)


async def init_db():
    """Crea la tabla si no existe. Llamar al iniciar cada servicio."""
    conn = await _get_connection()
    try:
        await conn.execute(CREATE_TABLE_SQL)
        logger.info("[conversation_store] Tabla conversations lista.")
    finally:
        await conn.close()


async def save_conversation(customer_id: str, service: str, messages: list) -> None:
    """
    Guarda el historial de mensajes al finalizar una conversación.
    
    Args:
        customer_id: ID del cliente
        service: nombre del servicio que manejó la conversación (master, loans, etc.)
        messages: lista de mensajes LangChain serializados
    """
    serialized = [
        {"role": _get_role(m), "content": m.content}
        for m in messages
        if hasattr(m, "content") and m.content
    ]

    conn = await _get_connection()
    try:
        await conn.execute(
            """
            INSERT INTO conversations (customer_id, service, messages, created_at)
            VALUES ($1, $2, $3, $4)
            """,
            customer_id,
            service,
            json.dumps(serialized),
            datetime.now(timezone.utc),
        )
        logger.info(f"[conversation_store] Conversación guardada: customer={customer_id} service={service} msgs={len(serialized)}")
    except Exception as e:
        logger.error(f"[conversation_store] Error guardando conversación: {e}")
    finally:
        await conn.close()


def _get_role(message) -> str:
    class_name = type(message).__name__
    if class_name == "HumanMessage":
        return "user"
    elif class_name == "AIMessage":
        return "assistant"
    elif class_name == "SystemMessage":
        return "system"
    return "unknown"
