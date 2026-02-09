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
    Ejecuta el nuevo perfil de inversión de un cliente.
    """
    if customer_id == "UNKNOWN" or not customer_id:
        return f"Error: No se proporcionó un ID de cliente válido. Customer ID recibido: {customer_id}"

    url = f"{JAVA_BASE_URL}/new-profile-investor/{customer_id}"
    response = requests.post(url, json=payload, timeout=5)
    if response.status_code == 200:
        return response.json()
    logger.error("Error: %s %s", response.status_code, response.text)
    return f"Error: {response.status_code} {response.text}"

