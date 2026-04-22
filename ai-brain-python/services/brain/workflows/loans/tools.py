import httpx
import os
from langchain_core.tools import tool

CORE_API = os.getenv("CORE_API_URL", "http://localhost:8080/api/v1/bank-ia")


# Funciones de lectura - llamadas directamente por nodo_cargar_datos
def fetch_customer_loans(customer_id: str) -> list:
    response = httpx.get(f"{CORE_API}/loans/{customer_id}")
    return response.json()


def fetch_refinanceable_loans(customer_id: str) -> list:
    response = httpx.get(f"{CORE_API}/loans/{customer_id}/to-cancel")
    return response.json()


def fetch_available_offers(customer_id: str) -> list:
    response = httpx.get(f"{CORE_API}/{customer_id}/available-offer")
    return response.json()


# Tools destructivas - el LLM las llama con confirmación previa
@tool
def create_new_loan(customer_id: str, amount: float, quotas: int, rate: float) -> dict:
    """Crea un nuevo préstamo para el cliente con el monto, cuotas y tasa indicados."""
    response = httpx.post(
        f"{CORE_API}/new-loan/{customer_id}",
        json={"amount": amount, "quotas": quotas, "rate": rate}
    )
    return response.json()


@tool
def execute_refinance(customer_id: str, loan_id: str, new_quotas: int) -> dict:
    """Ejecuta la refinanciación de un préstamo existente del cliente."""
    response = httpx.post(
        f"{CORE_API}/refinance",
        json={"customerId": customer_id, "loanId": loan_id, "newQuotas": new_quotas}
    )
    return response.json()


DESTRUCTIVE_TOOLS = [create_new_loan, execute_refinance]
DESTRUCTIVE_TOOL_NAMES = {t.name for t in DESTRUCTIVE_TOOLS}
