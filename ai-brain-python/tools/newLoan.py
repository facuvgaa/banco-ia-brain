import requests
import langchain.tools as tools
import logging


logging.basicConfig(filename='newLoan.log', level=logging.DEBUG)
logger = logging.getLogger(__name__)

JAVA_BASE_URL = "http://localhost:8080/api/v1/bank-ia"


def OfferLoan(customer_id: str):
    """
    Consulta el historial de transacciones de un cliente en el Core Bancario.
    Útil para verificar pagos fallidos, duplicados o estados de cuenta.
    """
    if customer_id == 'UNKNOWN' or not customer_id:
        return f"Error: No se proporcionó un ID de cliente válido. Customer ID recibido: {customer_id}"
    
    url = f"{JAVA_BASE_URL}/{customer_id}/available-offer"
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
        return response.json()
    else:
        return f"Error: {response.status_code} {response.text}"     
        logger.error(f"Error: {response.status_code} {response.text}")


def newLoan(customer_id: str):
    """
    Consulta el historial de transacciones de un cliente en el Core Bancario.
    Útil para verificar pagos fallidos, duplicados o estados de cuenta.
    """
    if customer_id == 'UNKNOWN' or not customer_id:
        return f"Error: No se proporcionó un ID de cliente válido. Customer ID recibido: {customer_id}"
    
    url = f"{JAVA_BASE_URL}/loans/{customer_id}"
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
        return response.json()
    else:
        return f"Error: {response.status_code} {response.text}"     
        logger.error(f"Error: {response.status_code} {response.text}")

def OfferLoan_tool():
    return tools.Tool(
        name="OfferLoan",
        description="Consulta de prestamos bancarios, disponibles para el cliente.",
        func=OfferLoan,
    )

def newLoan_tool():
    return tools.Tool(
        name="newLoan",
        description="Consulta de prestamos bancarios, disponibles para el cliente.",
        func=newLoan,
    )