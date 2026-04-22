import logging
import re

from services.llms.models import get_bedrock_model_master

model = get_bedrock_model_master()
logger = logging.getLogger(__name__)

PROMPT = """El asistente acaba de preguntar si el usuario necesitaba **algo más** o si podía **ayudar con otra cosa**.

Con el **siguiente mensaje** del usuario, clasificá:

- **CERRAR** — se despide, agradece, dice que no, que no necesita nada, “nada más”, “eso es todo”, “listo”, “chau”, “gracias no”, respuestas muy cortas de cierre.
- **NUEVO** — pide otra consulta, tema distinto, “sí quiero…”, pregunta nueva, pide otra explicación, inicia otra duda, “y sobre…”, “otra pregunta”.

Regla: si hay **cualquier** intención de seguir pidiendo información o de un **tema nuevo**, respondé **NUEVO**. Si es solo cierre, **CERRAR**.

Respondé con **una sola palabra**: CERRAR o NUEVO (sin puntuación).

Mensaje del usuario:
{message}"""


def get_post_close_route(message_content: str) -> str:
    """
    Retorna "close" | "reclassify".
    Se prefiere reclassify ante dudas para no dejar al usuario sin respuesta.
    """
    try:
        raw = (model.invoke(PROMPT.format(message=message_content)).content or "").strip()
    except Exception as e:
        logger.error("post_close router: %s", e)
        return "reclassify"
    u = (raw or "").upper()
    m = re.search(r"\b(CERRAR|NUEVO)\b", u)
    if m and m.group(1) == "CERRAR":
        return "close"
    return "reclassify"
