"""
Construcción de contexto para el agente: préstamos elegibles / ofertas o historial de transacciones.
Centraliza la lógica de qué datos traer según reason/category y el formateo para el prompt.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Union

from tools.refinance_tool import _get_refinance_context_impl
from tools.tool_customer_transaction import _get_customer_transactions_impl


@dataclass
class ContextResult:
    """Resultado del armado de contexto para el agente."""
    context_info: str
    ref_data: Union[Dict[str, Any], str, None]
    loan_number_to_id_map: Dict[str, str]
    eligible_loans_list: List[Dict[str, Any]]


def format_transactions(transactions: Union[List[Dict[str, Any]], str]) -> str:
    """Formatea las transacciones para el prompt."""
    if not transactions:
        return "No hay transacciones disponibles."
    if isinstance(transactions, str):
        return transactions
    if not isinstance(transactions, list):
        return "No hay transacciones disponibles."
    formatted: List[str] = []
    for txn in transactions[:10]:
        if isinstance(txn, dict):
            amount = str(txn.get("amount", "N/A"))
            status = str(txn.get("status", "N/A"))
            date = str(txn.get("transactionDate", "N/A"))
            description = str(txn.get("description", "N/A"))
            coelsa_id = str(txn.get("coelsaId", "N/A"))
            formatted.append(f"- {date}: ${amount} ({status}) - {description} [ID: {coelsa_id}]")
    return "\n".join(formatted) if formatted else "No hay transacciones disponibles."


def _should_fetch_loan_data(reason: str, category: str) -> bool:
    """Indica si debemos traer datos de préstamos/refinanciación según reason y category."""
    search_text = (reason + " " + category).upper().translate(str.maketrans("ÁÉÍÓÚ", "AEIOU"))
    is_loan_query = any(w in search_text for w in ["PRESTAMO", "REFINANCIACION", "DEUDA"])
    is_loan_category = category.upper() in ["PRESTAMO", "REFINANCIACION"]
    return is_loan_query or is_loan_category


def _build_loan_context(
    customer_id: str,
) -> tuple[str, Union[Dict[str, Any], str, None], Dict[str, str], List[Dict[str, Any]]]:
    """
    Obtiene y formatea contexto de préstamos elegibles y ofertas.
    Retorna: (context_info, ref_data, loan_number_to_id_map, eligible_loans_list).
    """
    context_info = ""
    loan_number_to_id_map: Dict[str, str] = {}
    eligible_loans_list: List[Dict[str, Any]] = []
    ref_data: Union[Dict[str, Any], str, None] = None

    try:
        ref_data = _get_refinance_context_impl(customer_id)
    except Exception as e:
        print(f"⚠️  Error consultando deudas: {e}")
        import traceback
        traceback.print_exc()
        return "\n\nError consultando deudas.", None, {}, []

    if not isinstance(ref_data, dict):
        context_info = f"\n\n[DATOS FINANCIEROS REALES]:\n{ref_data}"
        return context_info, ref_data, loan_number_to_id_map, eligible_loans_list

    eligible_loans = ref_data.get("eligible_loans", [])
    eligible_loans_list = eligible_loans if isinstance(eligible_loans, list) else []
    new_offers = ref_data.get("new_offers", [])

    context_info = "\n\n[DATOS FINANCIEROS REALES]:\n"
    context_info += f"Préstamos elegibles para refinanciar: {len(eligible_loans_list)}\n"
    all_loan_ids: List[str] = []

    for loan in eligible_loans_list:
        if not isinstance(loan, dict):
            continue
        loan_id = str(loan.get("id", "N/A"))
        loan_number = loan.get("loanNumber", "N/A")
        remaining = loan.get("remainingAmount", 0)
        paid = loan.get("paidQuotas", 0)
        total = loan.get("totalQuotas", 0)
        context_info += (
            f"- Préstamo {loan_number} (ID: {loan_id}): ${remaining} restantes "
            f"({paid}/{total} cuotas pagadas)\n"
        )
        if loan_number != "N/A" and loan_id != "N/A":
            loan_number_to_id_map[loan_number] = loan_id
            all_loan_ids.append(loan_id)

    if all_loan_ids:
        context_info += f"\n⚠️ IMPORTANTE: Debes incluir TODOS los {len(all_loan_ids)} préstamos en sourceLoanIds: {all_loan_ids}\n"

    context_info += f"\nOfertas nuevas disponibles: {len(new_offers)}\n"
    for offer in new_offers:
        if isinstance(offer, dict):
            context_info += (
                f"- Oferta: ${offer.get('maxAmount', 0)} máximo, "
                f"{offer.get('maxQuotas', 0)} cuotas, tasa {offer.get('monthlyRate', 0)}%\n"
            )

    return context_info, ref_data, loan_number_to_id_map, eligible_loans_list


def _build_transactions_context(customer_id: str) -> str:
    """Obtiene y formatea contexto de transacciones del cliente."""
    try:
        transactions: Union[List[Dict[str, Any]], str] = _get_customer_transactions_impl(customer_id)
        return f"\n\n[HISTORIAL DE TRANSACCIONES]:\n{format_transactions(transactions)}"
    except Exception as e:
        print(f"⚠️  Error al recuperar historial: {e}")
        return "\n\n⚠️ Error al recuperar historial."


def build_context(customer_id: str, reason: str, category: str) -> ContextResult:
    """
    Arma el contexto para el agente según customer_id, reason y category.
    - Si aplica préstamos/refinanciación: usa datos de refinance (elegibles + ofertas).
    - Si no: usa historial de transacciones.
    """
    context_info = ""
    ref_data: Union[Dict[str, Any], str, None] = None
    loan_number_to_id_map: Dict[str, str] = {}
    eligible_loans_list: List[Dict[str, Any]] = []

    if not customer_id or customer_id == "UNKNOWN":
        return ContextResult(
            context_info=context_info,
            ref_data=ref_data,
            loan_number_to_id_map=loan_number_to_id_map,
            eligible_loans_list=eligible_loans_list,
        )

    should_loan = _should_fetch_loan_data(reason, category)
    if should_loan:
        print(f"🚀 DEBUG: Entrando a lógica de PRESTAMOS para {customer_id} (categoría: {category})")
        context_info, ref_data, loan_number_to_id_map, eligible_loans_list = _build_loan_context(
            customer_id
        )
    else:
        context_info = _build_transactions_context(customer_id)

    return ContextResult(
        context_info=context_info,
        ref_data=ref_data,
        loan_number_to_id_map=loan_number_to_id_map,
        eligible_loans_list=eligible_loans_list,
    )
