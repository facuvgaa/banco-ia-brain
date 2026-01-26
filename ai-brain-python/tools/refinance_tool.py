import requests
from langchain.tools import Tool 


JAVA_BASE_URL = "http://localhost:8080/api/v1"

def _get_refinance_context_impl(customer_id: str):
    """
    Busca préstamos aptos para cancelar y ofertas de crédito vigentes.
    Indispensable para que la IA analice si al cliente le conviene refinanciar.
    """
    if not customer_id or customer_id == 'UNKNOWN':
        return "Error: ID de cliente inválido."
    
    try:
        to_cancel = requests.get(f"{JAVA_BASE_URL}/loans/{customer_id}/to-cancel", timeout=5).json()
        offers = requests.get(f"{JAVA_BASE_URL}/available-offer/{customer_id}", timeout=5).json()
        
        return {
            "eligible_loans": to_cancel,
            "new_offers": offers
        }
    except Exception as e:
        return f"Error al obtener contexto de refinanciación: {e}"

def _execute_refinance_impl(payload: dict):
    """
    Ejecuta la refinanciación final enviando el DTO a Java.
    Requiere un diccionario con: customerId, loanIdsToCancel, newTotalAmount, quotas, etc.
    """
    try:
        response = requests.post(f"{JAVA_BASE_URL}/refinance", json=payload, timeout=10)
        if response.status_code == 200:
            return f"Éxito: Operación procesada. Detalles: {response.json()}"
        return f"Error en la refinanciación: {response.text}"
    except Exception as e:
        return f"Error de conexión con el Core Bancario: {e}"

get_refinance_context = Tool.from_function(
    func=_get_refinance_context_impl,
    name="get_refinance_context",
    description="Obtiene préstamos actuales y ofertas nuevas para calcular la refinanciación."
)

execute_refinance = Tool.from_function(
    func=_execute_refinance_impl,
    name="execute_refinance",
    description="Realiza el impacto final de la refinanciación. Usar solo tras confirmación del cliente."
)