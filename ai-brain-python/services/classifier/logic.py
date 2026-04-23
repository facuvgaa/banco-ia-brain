import logging
import re

from services.classifier.prompt import PROMPT_CLS
from services.llms.models import get_bedrock_model_master

model = get_bedrock_model_master()

logger = logging.getLogger(__name__)

# Evita que Haiku mande a master consultas de inversión (el módulo con test vive en to-brain).
_INVESTMENT_TO_BRAIN = re.compile(
    r"(\binversiones?\b|\binversión\b|\binvertir\b|perfil inversor|test de idoneidad|idoneidad|"
    r"mercado de capitales|fci|cedear|dónde invertir|donde invertir|mep|bonos?|letras del tesoro|"
    r"armar cartera|activos financieros|fondo común|módulo de inversion|riesgo de inversión|"
    r"ahora inversi|tema inversi)",
    re.I,
)


def get_classification(message_content: str) -> str:
    text = (message_content or "").strip()
    if _INVESTMENT_TO_BRAIN.search(text):
        logger.info("[classifier] Heurística inversión -> to-brain")
        return "to-brain"

    formatted_prompt = PROMPT_CLS.format(message_content=message_content)

    try:
        response = model.invoke(formatted_prompt)
        raw = (response.content or "").strip()
        m = re.search(r"\b(to-master|to-brain)\b", raw.lower())
        intent = m.group(1) if m else ""
        if intent:
            logger.info(f"[DEBUG] Haiku enrutó -> {intent}")
            return intent
        logger.warning(f"[DEBUG] Salida inesperada de Haiku: {raw!r} -> to-brain")
        return "to-brain"
    except Exception as e:
        logger.error("Error en clasificación con Bedrock: %s", e)
        return "to-brain"
