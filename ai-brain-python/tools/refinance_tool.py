import json
import re
import requests
from typing import Any, Dict, List

from langchain.tools import Tool


JAVA_BASE_URL = "http://localhost:8080/api/v1/bank-ia"
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

def _get_refinance_context_impl(customer_id: str):
    """
    Busca préstamos aptos para cancelar y ofertas de crédito vigentes.
    Indispensable para que la IA analice si al cliente le conviene refinanciar.
    """
    if not customer_id or customer_id == 'UNKNOWN':
        return "Error: ID de cliente inválido."
    
    try:
        to_cancel = requests.get(f"{JAVA_BASE_URL}/loans/{customer_id}/to-cancel", timeout=5).json()
        offers = requests.get(f"{JAVA_BASE_URL}/{customer_id}/available-offer/", timeout=5).json()
        
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
    description="Realiza el impacto final de la refinanciación. Usar solo tras confirmación del cliente.",
)


def normalize_execute_refinance_args(
    raw_args: Dict[str, Any],
    customer_id: str,
    loan_number_to_id_map: Dict[str, str],
    eligible_loan_ids: List[str],
) -> Dict[str, Any]:
    """
    Normaliza y valida los argumentos del tool call execute_refinance.
    - Parsea __arg1 (dict o JSON string) si viene en ese formato.
    - Unifica customerId.
    - Convierte loanNumber → UUID usando el mapeo.
    - Si hay eligible_loan_ids, valida y reemplaza sourceLoanIds por la lista oficial si hace falta.
    Retorna el payload listo para _execute_refinance_impl.
    """
    args = raw_args if isinstance(raw_args, dict) else {}

    # Parsear formato LangChain (__arg1)
    if "__arg1" in args:
        arg1 = args["__arg1"]
        if isinstance(arg1, dict):
            normalized = dict(arg1)
        elif isinstance(arg1, str):
            try:
                normalized = json.loads(arg1)
            except json.JSONDecodeError:
                normalized = {"payload": arg1}
        else:
            normalized = {k: v for k, v in args.items() if k != "__arg1"}
    else:
        normalized = dict(args)

    # customerId
    if "customer_id" in normalized and "customerId" not in normalized:
        normalized["customerId"] = normalized.pop("customer_id")
    if "customerId" not in normalized:
        normalized["customerId"] = customer_id

    # sourceLoanIds: traducir loanNumber → UUID y validar contra elegibles
    if "sourceLoanIds" not in normalized:
        normalized["sourceLoanIds"] = eligible_loan_ids if eligible_loan_ids else []
    else:
        source_loan_ids = normalized["sourceLoanIds"]
        if not isinstance(source_loan_ids, list):
            source_loan_ids = [source_loan_ids] if source_loan_ids else []

        corrected_ids: List[str] = []
        for loan_id in source_loan_ids:
            s = str(loan_id).strip()
            if s.startswith("LOAN-") and s in loan_number_to_id_map:
                corrected_ids.append(loan_number_to_id_map[s])
            else:
                corrected_ids.append(s)

        if eligible_loan_ids:
            valid_ids = [
                lid
                for lid in corrected_ids
                if UUID_PATTERN.match(lid) and lid in eligible_loan_ids
            ]
            if len(valid_ids) != len(eligible_loan_ids) or any(
                lid not in eligible_loan_ids for lid in corrected_ids
            ):
                corrected_ids = list(eligible_loan_ids)

        normalized["sourceLoanIds"] = corrected_ids

    return normalized


def refinance_args(
    customer_id: str,
    sourceLoanIds: List[str],
    offeredAmount: float,
    selectedQuotas: int,
    appliedRate: float,
    expectedCashOut: float,
) -> Dict[str, Any]:
    return {
        "customerId": customer_id,
        "sourceLoanIds": sourceLoanIds,
        "offeredAmount": offeredAmount,
        "selectedQuotas": selectedQuotas,
        "appliedRate": appliedRate,
        "expectedCashOut": expectedCashOut
    }