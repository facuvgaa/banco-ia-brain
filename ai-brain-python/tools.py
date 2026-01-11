import requests
from langchain.tools import Tool


@Tool
def get_customer_transactions(customer_id: str):

    """
    Consulta el historial de transacciones de un cliente en el Core Bancario.
    Útil para verificar pagos fallidos, duplicados o estados de cuenta.
    """
    url = f"http://localhost:8080/api/v1/internal/audit/transactions/{customer_id}"


    try:
        response = requests.get(url, timeout=05)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 204:
            return f"No se encontraron transacciones para el cliente {customer_id}"
        else:
            print(f"Error al obtener las transacciones: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Error al obtener las transacciones: {e}")
        return None