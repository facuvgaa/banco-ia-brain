import logging
from uuid import UUID

from langchain_core.messages import SystemMessage
from langgraph.types import interrupt
from services.brain.workflows.loans.state import LoanState
from services.brain.workflows.loans.tools import (
    fetch_customer_loans,
    fetch_refinanceable_loans,
    fetch_available_offers,
    DESTRUCTIVE_TOOL_NAMES,
)
from services.brain.workflows.loans.prompt import SYSTEM_PROMPT_LOANS
from services.brain.workflows.loans.loan_payload import enrich_loans_list, enrich_offers_list

logger = logging.getLogger(__name__)


def _norm_uuid(s) -> str:
    try:
        return str(UUID(str(s)))
    except (ValueError, TypeError):
        return str(s).strip().lower()


def _loan_numbers_for_refi_confirmation(loans: list, source_ids: list) -> str:
    """Para el resumen al usuario: solo números de préstamo visibles, nunca UUIDs."""
    if not source_ids:
        return "tus préstamos seleccionados"
    by_id: dict[str, str] = {}
    for l in loans or []:
        lid = l.get("id")
        if lid is None:
            continue
        by_id[_norm_uuid(lid)] = (l.get("loanNumber") or l.get("loan_number") or "").strip() or "préstamo"
    labels = []
    for raw in source_ids:
        num = by_id.get(_norm_uuid(raw))
        if num:
            labels.append(num)
        else:
            labels.append("un préstamo a liquidar")
    if len(set(labels)) == 1 and labels[0] == "un préstamo a liquidar":
        return "el préstamo a liquidar"
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} y {labels[1]}"
    return ", ".join(labels[:-1]) + f" y {labels[-1]}"


def load_data_node(state: LoanState) -> dict:
    customer_id = state["customer_id"]
    logger.info(f"[loans] Cargando datos para cliente {customer_id}")

    loans = enrich_loans_list(fetch_customer_loans(customer_id))
    refinanceable = enrich_loans_list(fetch_refinanceable_loans(customer_id))
    offers = enrich_offers_list(fetch_available_offers(customer_id))

    return {
        "loans": loans,
        "refinanceable": refinanceable,
        "offers": offers,
    }


def agent_node(state: LoanState, model) -> dict:
    prompt = SYSTEM_PROMPT_LOANS.format(
        customer_id=state["customer_id"],
        loans=state["loans"],
        refinanceable=state["refinanceable"],
        offers=state["offers"],
    )
    messages = [SystemMessage(content=prompt)] + state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


def confirmation_node(state: LoanState) -> dict:
    tool_call = state["messages"][-1].tool_calls[0]
    tool_name = tool_call["name"]
    args = tool_call["args"]

    if tool_name == "create_new_loan":
        resumen = (
            f"Estás a punto de solicitar un préstamo:\n"
            f"- Monto: ${args['amount']:,.0f}\n"
            f"- Cuotas: {args['quotas']}\n"
            f"- Tasa: {args['rate']}% TNA\n\n"
            f"¿Confirmás? (sí / no)"
        )
    elif tool_name == "execute_refinance":
        ids = args.get("source_loan_ids") or ([args["loan_id"]] if args.get("loan_id") else [])
        cuotas = args.get("selected_quotas", args.get("new_quotas"))
        monto = float(args.get("offered_amount") or args.get("offeredAmount") or 0)
        tna = args.get("applied_rate", args.get("appliedRate"))
        cash = float(args.get("expected_cash_out") or args.get("expectedCashOut") or 0)
        ref_label = _loan_numbers_for_refi_confirmation(state.get("loans") or [], ids)
        resumen = (
            f"Estás a punto de refinanciar: {ref_label}.\n"
            f"- Monto del nuevo préstamo: ${monto:,.0f}\n"
            f"- Cuotas: {cuotas} | TNA: {tna}%\n"
            f"- Efectivo en mano (estimado): ${cash:,.0f}\n\n"
            f"¿Confirmás? (sí / no)"
        )
    else:
        resumen = f"¿Confirmás la operación {tool_name}? (sí / no)"

    respuesta = interrupt(resumen)
    confirmed = "sí" in respuesta.lower() or "si" in respuesta.lower()

    logger.info(f"[loans] Confirmación de {tool_name}: {confirmed}")
    return {"confirmed": confirmed}
