import json
import logging
import requests
from typing import Any, Dict

from langchain.tools import Tool

logger = logging.getLogger(__name__)

JAVA_BASE_URL = "http://localhost:8080/api/v1/bank-ia"


def OfferLoan(customer_id: str):
    """
    Consulta las ofertas de préstamo disponibles para un cliente en el Core Bancario.
    """
    if customer_id == "UNKNOWN" or not customer_id:
        return f"Error: No se proporcionó un ID de cliente válido. Customer ID recibido: {customer_id}"

    url = f"{JAVA_BASE_URL}/{customer_id}/available-offer"
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
        return response.json()
    logger.error("Error: %s %s", response.status_code, response.text)
    return f"Error: {response.status_code} {response.text}"


def _execute_new_loan_impl(payload: Dict[str, Any]) -> str:
    """
    Ejecuta el alta de un nuevo préstamo en el Core.
    payload debe tener: customerId (para la URL), amount, quotas, rate (para el body).
    """
    customer_id = payload.get("customerId") or payload.get("customer_id")
    if not customer_id or customer_id == "UNKNOWN":
        return "Error: No se proporcionó un ID de cliente válido."

    amount = payload.get("amount")
    quotas = payload.get("quotas")
    rate = payload.get("rate")
    if amount is None or quotas is None or rate is None:
        return "Error: Faltan parámetros. Se requieren amount, quotas y rate."

    url = f"{JAVA_BASE_URL}/new-loan/{customer_id}"
    body = {"amount": float(amount), "quotas": int(quotas), "rate": float(rate)}
    try:
        response = requests.post(url, json=body, timeout=10)
        if response.status_code in (200, 201):
            data = response.json() if response.content else {}
            return f"Éxito: Nuevo préstamo creado. Detalles: {data}"
        try:
            err = response.json()
            detail = err.get("message", err) if isinstance(err, dict) else err
        except Exception:
            detail = response.text or response.reason or f"HTTP {response.status_code}"
        return f"Error en nuevo préstamo (HTTP {response.status_code}): {detail}"
    except Exception as e:
        logger.exception("Error de conexión al ejecutar nuevo préstamo")
        return f"Error de conexión con el Core Bancario: {e}"


def normalize_new_loan_args(raw_args: Dict[str, Any], customer_id: str) -> Dict[str, Any]:
    """
    Normaliza los argumentos del tool call execute_new_loan.
    Acepta __arg1 (dict o JSON string) como en refinance y unifica customerId, amount, quotas, rate.
    """
    args = raw_args if isinstance(raw_args, dict) else {}

    if "__arg1" in args:
        arg1 = args["__arg1"]
        if isinstance(arg1, dict):
            normalized = dict(arg1)
        elif isinstance(arg1, str):
            try:
                normalized = json.loads(arg1)
            except json.JSONDecodeError:
                normalized = {}
        else:
            normalized = {k: v for k, v in args.items() if k != "__arg1"}
    else:
        normalized = dict(args)

    if "customer_id" in normalized and "customerId" not in normalized:
        normalized["customerId"] = normalized.pop("customer_id")
    if "customerId" not in normalized:
        normalized["customerId"] = customer_id

    for key in ("amount", "quotas", "rate"):
        if key not in normalized and key in args:
            normalized[key] = args[key]

    return normalized


execute_new_loan = Tool.from_function(
    func=_execute_new_loan_impl,
    name="execute_new_loan",
    description=(
        "Tomar un nuevo préstamo cuando el cliente tiene oferta pero no puede refinanciar. "
        "Parámetros: amount (monto), quotas (número de cuotas), rate (tasa). "
        "Usar solo cuando hay oferta disponible y el cliente acepta."
    ),
)


def OfferLoan_tool():
    return Tool(
        name="OfferLoan",
        description="Consulta las ofertas de préstamo disponibles para el cliente.",
        func=OfferLoan,
    )
