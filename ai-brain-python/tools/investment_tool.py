from langchain.tools import Tool
import re
import requests
import logging

logger = logging.getLogger(__name__)

JAVA_BASE_URL = "http://localhost:8080/api/v1/bank-ia"

# ---------------------------------------------------------------------------
# Tracking de sesiones activas de inversión (in-memory)
# Cuando el cuestionario de perfil está en curso, el customer_id se agrega acá
# para que el triage sepa que los siguientes mensajes son respuestas y los
# escale directo al brain sin pasar por el LLM de triage.
# ---------------------------------------------------------------------------
_active_investment_sessions: set = set()


def mark_investment_session_active(customer_id: str) -> None:
    """Marca al cliente como en medio del cuestionario de inversión."""
    _active_investment_sessions.add(customer_id)
    logger.debug("Sesión inversión ACTIVA para %s", customer_id)


def mark_investment_session_complete(customer_id: str) -> None:
    """Marca el cuestionario como completo y libera la sesión."""
    _active_investment_sessions.discard(customer_id)
    logger.debug("Sesión inversión COMPLETA para %s", customer_id)


def is_investment_session_active(customer_id: str) -> bool:
    """Devuelve True si el cliente está en medio del cuestionario de inversión."""
    return customer_id in _active_investment_sessions

# ---------------------------------------------------------------------------
# Helpers del cuestionario de inversiones (flujo pregunta-por-pregunta)
# ---------------------------------------------------------------------------

def _investment_profile_summary(risk_level: str, max_loss, horizon: str) -> str:
    """Genera un resumen legible del perfil de inversor completo."""
    horizon_labels = {"SHORT": "corto plazo", "MEDIUM": "mediano plazo", "LONG": "largo plazo"}
    horizon_label = horizon_labels.get((horizon or "").upper(), horizon or "no especificado")
    risk_labels = {
        "CONSERVADOR": "Conservador",
        "MODERADO": "Moderado",
        "AGRESIVO": "Agresivo",
        "SUPER_AGRESIVO": "Súper Agresivo",
    }
    risk_label = risk_labels.get((risk_level or "").upper(), risk_level or "no definido")
    loss_line = f"• Pérdida máxima aceptada: {max_loss}%\n" if max_loss is not None else ""
    return (
        f"¡Listo! Tu perfil de inversor quedó configurado:\n\n"
        f"• Nivel de riesgo: {risk_label}\n"
        f"{loss_line}"
        f"• Horizonte de inversión: {horizon_label}\n\n"
        f"Ahora puedo informarte sobre los productos de inversión disponibles según tu perfil. "
        f"¿Querés que te cuente sobre bonos, fondos de inversión, plazo fijo o dólar MEP?"
    )


def _build_investment_next_step(profile_data: dict) -> str:
    """Analiza el perfil y devuelve la siguiente pregunta o el resumen final.

    Python controla el flujo pregunta-por-pregunta sin necesidad de llamar a Bedrock.
    """
    if not isinstance(profile_data, dict):
        return "Hubo un error al consultar tu perfil de inversor. ¿Podés intentar de nuevo?"

    risk_level = profile_data.get("riskLevel")
    max_loss = profile_data.get("maxLossPercent")
    horizon = profile_data.get("horizon")

    # Perfil completo → resumen
    if risk_level and max_loss is not None and horizon:
        return _investment_profile_summary(risk_level, max_loss, horizon)

    # Preguntas en orden: riskLevel → maxLossPercent → horizon
    if not risk_level:
        return (
            "Para armar tu perfil de inversor necesito hacerte unas preguntas.\n\n"
            "Empecemos: ¿qué nivel de riesgo aceptás para tus inversiones?\n\n"
            "• Bajo: preferís seguridad, aunque la ganancia sea menor.\n"
            "• Medio: aceptás algo de riesgo por una ganancia razonable.\n"
            "• Alto: estás dispuesto a asumir riesgos importantes por mayor ganancia."
        )

    if max_loss is None:
        return (
            f"Perfecto, registré tu nivel de riesgo como {risk_level}. "
            "Ahora necesito saber: en el peor de los escenarios, "
            "¿cuánto estarías dispuesto a perder de tu inversión inicial? "
            "Dame un porcentaje aproximado (ej: 5%, 15%, 30%)."
        )

    # Solo falta horizon
    return (
        "Última pregunta: ¿en cuánto tiempo pensás que vas a necesitar esta plata?\n\n"
        "• Corto plazo: menos de 1 año.\n"
        "• Mediano plazo: entre 1 y 3 años.\n"
        "• Largo plazo: más de 3 años."
    )


def _interpret_questionnaire_answer(user_text: str, profile_data: dict) -> dict | None:
    """Interpreta la respuesta del usuario al cuestionario SIN usar un LLM.

    Analiza cada campo faltante en orden (riskLevel → maxLossPercent → horizon)
    e intenta extraer la respuesta del texto del usuario con keyword matching.
    Si el usuario responde varias preguntas a la vez, extrae todas.

    Devuelve un dict con los campos a actualizar, o None si no puede interpretar.
    """
    if not isinstance(profile_data, dict):
        return None

    t = user_text.lower().strip()
    updates: dict = {}

    # ── riskLevel ──
    if not profile_data.get("riskLevel"):
        if any(w in t for w in ("bajo", "conservador", "seguridad", "seguro", "no quiero perder")):
            updates["riskLevel"] = "CONSERVADOR"
        elif any(w in t for w in ("muy alto", "super agresivo", "súper agresivo", "máximo riesgo")):
            updates["riskLevel"] = "SUPER_AGRESIVO"
        elif any(w in t for w in ("medio", "moderado", "balance", "equilibr")):
            updates["riskLevel"] = "MODERADO"
        elif any(w in t for w in ("alto", "agresivo", "arriesgar", "mucho riesgo", "máxima ganancia")):
            updates["riskLevel"] = "AGRESIVO"

    # ── maxLossPercent ──
    if profile_data.get("maxLossPercent") is None:
        match = re.search(r'(\d+)\s*(%|por\s*ciento|porciento)?', t)
        if match:
            num = int(match.group(1))
            if 0 < num <= 100:
                updates["maxLossPercent"] = num

    # ── horizon ──
    if not profile_data.get("horizon"):
        if any(w in t for w in ("corto", "meses", "ya mismo", "pronto", "inmediato")):
            updates["horizon"] = "SHORT"
        elif any(w in t for w in ("largo", "más de 3", "mas de 3", "muchos años", "5 años", "10 años")):
            updates["horizon"] = "LONG"
        elif any(w in t for w in ("mediano", "año", "años", "1 a 3", "un par", "par de")):
            updates["horizon"] = "MEDIUM"

    return updates if updates else None


# ---------------------------------------------------------------------------
# Funciones de API REST
# ---------------------------------------------------------------------------

def get_profile_investor(customer_id: str) -> dict:
    """
    Obtiene el perfil de inversión de un cliente.
    """

    if customer_id == "UNKNOWN" or not customer_id:
        return f"Error: No se proporcionó un ID de cliente válido. Customer ID recibido: {customer_id}"

    url = f"{JAVA_BASE_URL}/profile-investor/{customer_id}"
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
        return response.json()
    logger.error("Error: %s %s", response.status_code, response.text)
    return f"Error: {response.status_code} {response.text}"

def execute_new_profile_investor(customer_id: str, payload: dict):
    """
    Ejecuta la creación o actualización del perfil de inversión de un cliente.
    payload: dict con riskLevel, hasProfile, maxLossPercent, horizon (camelCase).
    """
    if customer_id == "UNKNOWN" or not customer_id:
        return f"Error: No se proporcionó un ID de cliente válido. Customer ID recibido: {customer_id}"

    url = f"{JAVA_BASE_URL}/new-profile-investor/{customer_id}"
    response = requests.post(url, json=payload, timeout=5)
    if response.status_code == 200:
        return response.json()
    logger.error("Error: %s %s", response.status_code, response.text)
    return f"Error: {response.status_code} {response.text}"


def _create_profile_impl(args):
    """Extrae customer_id y arma el payload (camelCase) desde los args que envía el LLM.

    IMPORTANTE: primero obtiene el perfil actual del cliente y hace merge,
    así un update parcial (ej. solo riskLevel) no pisa los campos que ya
    tenían valor (maxLossPercent, horizon, etc.).
    """
    if not isinstance(args, dict):
        return "Error: se esperaba un diccionario de argumentos."
    # Soporte formato LangChain (__arg1)
    if "__arg1" in args:
        arg1 = args["__arg1"]
        args = arg1 if isinstance(arg1, dict) else args
    customer_id = args.get("customer_id") or args.get("customerId")
    if not customer_id:
        return "Error: falta customer_id."

    snake_to_camel = {
        "risk_level": "riskLevel",
        "has_profile": "hasProfile",
        "max_loss_percent": "maxLossPercent",
        "horizon": "horizon",
    }

    # ── Merge: obtener perfil actual para no pisar campos existentes ──
    current = get_profile_investor(customer_id)
    if isinstance(current, dict):
        payload = {
            "riskLevel": current.get("riskLevel"),
            "hasProfile": current.get("hasProfile", False),
            "maxLossPercent": current.get("maxLossPercent"),
            "horizon": current.get("horizon"),
        }
    else:
        payload = {"hasProfile": False}

    # Sobreescribir solo los campos que el LLM envió (no-None)
    for k, v in args.items():
        if k in ("customer_id", "customerId"):
            continue
        key = snake_to_camel.get(k, k)
        if v is not None:
            payload[key] = v

    # Determinar hasProfile automáticamente: true solo si los 3 campos están completos
    if payload.get("riskLevel") and payload.get("maxLossPercent") is not None and payload.get("horizon"):
        payload["hasProfile"] = True

    return execute_new_profile_investor(customer_id, payload)


get_risk_profile = Tool.from_function(
    func=get_profile_investor,
    name="get_risk_profile",
    description="Obtiene el perfil de inversor del cliente. Usar para saber si ya completó el cuestionario (hasProfile) y su nivel de riesgo (riskLevel). Si hasProfile es false, hay que hacerle las preguntas antes de ofrecer productos."
)

create_or_update_profile_investor = Tool.from_function(
    func=_create_profile_impl,
    name="create_or_update_profile_investor",
    description="Crea o actualiza el perfil de inversor del cliente. Usar cuando el cliente complete el cuestionario. Parámetros (dict): customer_id, riskLevel, hasProfile, maxLossPercent, horizon."
)