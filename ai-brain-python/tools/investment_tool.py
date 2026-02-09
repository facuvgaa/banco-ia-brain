from langchain.tools import Tool
import requests
import logging

logger = logging.getLogger("investment_tool",__name__)

JAVA_BASE_URL = "http://localhost:8080/api/v1/bank-ia"

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
    """Extrae customer_id y arma el payload (camelCase) desde los args que envía el LLM."""
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
    payload = {}
    for k, v in args.items():
        if k in ("customer_id", "customerId"):
            continue
        key = snake_to_camel.get(k, k)
        payload[key] = v
    payload = {k: v for k, v in payload.items() if v is not None}
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