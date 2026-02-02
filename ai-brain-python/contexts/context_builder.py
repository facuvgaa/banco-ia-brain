"""
Construcción de contexto para el agente: préstamos elegibles / ofertas o historial de transacciones.
Centraliza la lógica de qué datos traer según reason/category y el formateo para el prompt.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Union
from tools.refinance_tool import _get_refinance_context_impl
from tools.tool_customer_transaction import _get_customer_transactions_impl

import logging

logging.basicConfig(filename='context_builder.log', level=logging.DEBUG)
logger = logging.getLogger(__name__)

@dataclass
class ContextResult:
    """Resultado del armado de contexto para el agente."""
    context_info: str
    ref_data: Union[Dict[str, Any], str, None]
    loan_number_to_id_map: Dict[str, str]
    eligible_loans_list: List[Dict[str, Any]]
    best_offer_summary: Dict[str, Any]


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
) -> tuple[str, Union[Dict[str, Any], str, None], Dict[str, str], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Obtiene y formatea contexto de préstamos elegibles y ofertas.
    Retorna: (context_info, ref_data, loan_number_to_id_map, eligible_loans_list, best_offer_summary).
    """
    context_info = ""
    loan_number_to_id_map: Dict[str, str] = {}
    eligible_loans_list: List[Dict[str, Any]] = []
    ref_data: Union[Dict[str, Any], str, None] = None
    empty_summary: Dict[str, Any] = {}

    try:
        ref_data = _get_refinance_context_impl(customer_id)
    except Exception as e:
        logging.debug(f"⚠️  Error consultando deudas: {e}")
        import traceback
        logging.debug(traceback.print_exc())
        return "\n\nError consultando deudas.", None, {}, [], empty_summary

    if not isinstance(ref_data, dict):
        context_info = f"\n\n[DATOS FINANCIEROS REALES]:\n{ref_data}"
        return context_info, ref_data, loan_number_to_id_map, eligible_loans_list, empty_summary

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

    total_debt = sum(
        float(loan.get("remainingAmount", 0))
        for loan in eligible_loans_list
        if isinstance(loan, dict)
    )

    context_info += (
        f"\nOferta de nuevo préstamo disponible (para pagar los anteriores y dar efectivo): "
        f"{len(new_offers)} oferta(s). Deuda total a cubrir: ${total_debt:,.0f}.\n"
    )

    # Todas las ofertas que cubren la deuda: monto, cuotas, tasa, sobrante. El cliente elige una.
    eligible_offers: List[Dict[str, Any]] = []
    for offer in new_offers:
        if not isinstance(offer, dict):
            continue
        m = float(offer.get("maxAmount", 0) or 0)
        if m < total_debt:
            continue
        cuotas = offer.get("maxQuotas", 0)
        tasa = offer.get("monthlyRate", 0)
        sobrante = m - total_debt
        eligible_offers.append({
            "monto": m,
            "cuotas": cuotas,
            "tasa": float(tasa) if tasa is not None else 0,
            "sobrante": sobrante,
        })

    best_offer_summary: Dict[str, Any] = {}
    if eligible_offers:
        # Ordenar por monto (asc) para mostrar de menor a mayor; el modelo explica trade-offs
        eligible_offers.sort(key=lambda x: (x["monto"], x["tasa"]))
        context_info += (
            "\n⚠️ OPCIONES DE REFINANCIACIÓN (presentá todas; el cliente elige una). "
            "Usá SOLO los números de la opción que elija. No inventes.\n"
        )
        for i, o in enumerate(eligible_offers, 1):
            m, c, t, s = o["monto"], o["cuotas"], o["tasa"], o["sobrante"]
            # Breve trade-off: más monto = más efectivo pero suele ser más cuotas/tasa (más interés)
            if t >= 85:
                nota = " — Tasa alta: más interés total; advertir al cliente."
            elif c >= 48:
                nota = " — Más cuotas: cuota mensual más baja, más interés total."
            elif t <= 70:
                nota = " — Tasa más baja: menor costo total."
            else:
                nota = ""
            context_info += (
                f"- Opción {i}: ${m:,.0f} a {c} cuotas, tasa {t}% → sobrante en efectivo: ${s:,.0f}{nota}\n"
            )
        context_info += (
            f"\nDeuda total: ${total_debt:,.0f}. "
            "Explicá: más monto = más efectivo pero puede implicar más cuotas o tasa más alta (más interés). "
            "Menos tasa = menor costo. Más cuotas = cuota mensual más baja. "
            "Cuando el cliente elija una opción, usá ESA oferta para execute_refinance (esos números exactos).\n"
        )
        # Para el prompt: lista de opciones (la "mejor" por defecto puede ser la de tasa más baja)
        best_offer_summary = {
            "deuda_total": total_debt,
            "opciones": eligible_offers,
            "recomendada_tasa_baja": min(eligible_offers, key=lambda x: x["tasa"]) if eligible_offers else {},
        }
    else:
        context_info += (
            "\n⚠️ Se consultó la oferta disponible para pagar estos préstamos; ninguna cubre la deuda o no hay ofertas. "
            "PROHIBIDO INVENTAR montos, tasas ni sobrante. "
            "Decile al cliente que en este momento no hay ofertas de refinanciación disponibles o que consulte más tarde.\n"
        )

    return context_info, ref_data, loan_number_to_id_map, eligible_loans_list, best_offer_summary


def _build_transactions_context(customer_id: str) -> str:
    """Obtiene y formatea contexto de transacciones del cliente."""
    try:
        transactions: Union[List[Dict[str, Any]], str] = _get_customer_transactions_impl(customer_id)
        return f"\n\n[HISTORIAL DE TRANSACCIONES]:\n{format_transactions(transactions)}"
    except Exception as e:
        logging.debug(f"⚠️  Error al recuperar historial: {e}")
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

    best_offer_summary: Dict[str, Any] = {}
    if not customer_id or customer_id == "UNKNOWN":
        return ContextResult(
            context_info=context_info,
            ref_data=ref_data,
            loan_number_to_id_map=loan_number_to_id_map,
            eligible_loans_list=eligible_loans_list,
            best_offer_summary=best_offer_summary,
        )

    should_loan = _should_fetch_loan_data(reason, category)
    if should_loan:
        logging.debug(f"🚀 DEBUG: Entrando a lógica de PRESTAMOS para {customer_id} (categoría: {category})")
        context_info, ref_data, loan_number_to_id_map, eligible_loans_list, best_offer_summary = _build_loan_context(
            customer_id
        )
    else:
        context_info = _build_transactions_context(customer_id)

    return ContextResult(
        context_info=context_info,
        ref_data=ref_data,
        loan_number_to_id_map=loan_number_to_id_map,
        eligible_loans_list=eligible_loans_list,
        best_offer_summary=best_offer_summary,
    )


def get_eligible_loan_ids(ctx: ContextResult, customer_id: str) -> List[str]:
    """
    Obtiene la lista de UUIDs de préstamos elegibles a partir del contexto.
    Si el contexto no tiene datos (ej. categoría transacciones), intenta obtenerlos de la API.
    """
    eligible_loans_from_data: List[Dict[str, Any]] = []
    if isinstance(ctx.ref_data, dict):
        eligible_loans_from_data = ctx.ref_data.get("eligible_loans", []) or []
    if not eligible_loans_from_data and ctx.eligible_loans_list:
        eligible_loans_from_data = ctx.eligible_loans_list
    if not eligible_loans_from_data:
        try:
            fresh = _get_refinance_context_impl(customer_id)
            if isinstance(fresh, dict):
                eligible_loans_from_data = fresh.get("eligible_loans", []) or []
        except Exception:
            pass
    return [
        str(loan.get("id", ""))
        for loan in eligible_loans_from_data
        if isinstance(loan, dict) and loan.get("id")
    ]


def refinance_success_message(customer_id: str, amount_credited: float) -> str:
    """
    Mensaje de éxito tras una refinanciación. Debe indicar explícitamente
    cuánta plata se le agregó/acreditó a la cuenta del cliente.
    """
    amount_str = f"${amount_credited:,.2f}"
    return (
        f"¡Excelente! La refinanciación se ha completado exitosamente. "
        f"Todos tus préstamos fueron consolidados en un nuevo préstamo. "
        f"Se te agregó {amount_str} a tu cuenta (dinero sobrante acreditado). "
        f"Podés verificar el nuevo préstamo y el saldo actualizado en tu cuenta."
    )