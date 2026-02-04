import requests
from langchain.tools import Tool


def _get_customer_transactions_impl(customer_id: str):
    """
    Consulta el historial de transacciones de un cliente en el Core Bancario.
    Útil para verificar pagos fallidos, duplicados o estados de cuenta.
    """
    if customer_id == 'UNKNOWN' or not customer_id:
        return f"Error: No se proporcionó un ID de cliente válido. Customer ID recibido: {customer_id}"
    
    url = f"http://localhost:8080/api/v1/bank-ia/transactions/{customer_id}"

    try:
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return f"No se encontraron transacciones para el cliente {customer_id}"
        else:
            error_msg = f"Error al obtener las transacciones: HTTP {response.status_code}"
            print(error_msg)
            return error_msg

    except requests.exceptions.RequestException as e:
        error_msg = f"Error de conexión al obtener las transacciones: {e}"
        print(error_msg)
        return error_msg


get_customer_transactions = Tool.from_function(
    func=_get_customer_transactions_impl,
    name="get_customer_transactions",
    description="Consulta el historial de transacciones de un cliente en el Core Bancario. Útil para verificar pagos fallidos, duplicados o estados de cuenta."
)