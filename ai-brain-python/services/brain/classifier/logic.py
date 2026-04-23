import re
import logging
from services.brain.classifier.prompt import PROMPT_BRAIN_CLS
from services.llms.models import get_bedrock_model_master

model = get_bedrock_model_master()

logger = logging.getLogger(__name__)

VALID_WORKFLOWS = ["workflow_loans", "workflow_investment"]

# Misma ventana que session: al expirar se vuelve a clasificar con Haiku si hace falta.
BRAIN_WORKFLOW_TTL_S = 1800

_BRAIN_INVEST = re.compile(
    r"(\binversiones?\b|\binversión\b|\binvertir\b|perfil inversor|test de idoneidad|idoneidad|"
    r"mercado de capitales|fci|cedear|dónde invertir|donde invertir|mep|bonos?|letras del tesoro|"
    r"armar cartera|activos financieros|fondo común|módulo de inversion|ahora inversi|tema inversi)",
    re.I,
)

_BRAIN_LOANS = re.compile(
    r"(\bpréstamo|\bprestamo|refinanc|refi\b|nuevo crédito|plata en mano|"
    r"efectivo en mano|mi préstamo|solicit(ar|o) (un )?préstamo|loan|mill[oó]n (de )?plata|tope 1[,.]?2)",
    re.I,
)


def should_reclassify_brain_workflow(
    cached: str, contenido_usuario: str
) -> bool:
    """
    Con caché activo, NO volver a llamar a Haiku salvo que el usuario indique
    el otro módulo en su mensaje (palabras clave solo en el texto del usuario).
    """
    if cached not in VALID_WORKFLOWS:
        return True
    u = (contenido_usuario or "").strip()
    if cached == "workflow_loans" and _BRAIN_INVEST.search(u) and not _BRAIN_LOANS.search(u):
        return True
    if cached == "workflow_investment" and _BRAIN_LOANS.search(u) and not _BRAIN_INVEST.search(u):
        return True
    return False


def get_brain_classification(
    contenido_usuario: str, ultimo_asistente: str | None = None
) -> str:
    """
    Si el cliente manda el último turno del asistente, Haiku resuelve intención con contexto
    (respuestas con sus palabras, letras A-D, “la primera opción”, etc.). Sin eso, heurística + Haiku.
    """
    c = (contenido_usuario or "").strip()
    a = (ultimo_asistente or "").strip()

    t = f"{a}\n{c}" if a else c
    if a == "" and _BRAIN_INVEST.search(t) and not _BRAIN_LOANS.search(t):
        logger.info("[BRAIN-CLS] Heurística -> workflow_investment")
        return "workflow_investment"
    if a == "" and _BRAIN_LOANS.search(t) and not _BRAIN_INVEST.search(t):
        logger.info("[BRAIN-CLS] Heurística -> workflow_loans")
        return "workflow_loans"

    formatted_prompt = PROMPT_BRAIN_CLS.format(
        ultimo_asistente=a or "(ninguno — el usuario inicia o no se envió contexto)",
        contenido_usuario=c or "(vacío)",
    )

    try:
        response = model.invoke(formatted_prompt)
        raw = (response.content or "").strip().lower() if isinstance(response.content, str) else str(
            response.content
        )
        m = re.search(
            r"\b(workflow_loans|workflow_investment|workflow_inversion)\b", raw, re.I
        )
        intent = (m.group(1).lower() if m else raw).replace("workflow_inversion", "workflow_investment")
        logger.info(f"[BRAIN-CLS] Haiku decidió -> {intent}")
        return intent if intent in VALID_WORKFLOWS else "workflow_loans"

    except Exception as e:
        logger.error(f"Error en la clasificacion brain: {e}")
        return "workflow_loans"


