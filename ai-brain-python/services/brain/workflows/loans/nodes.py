import logging
from langchain_core.messages import SystemMessage
from langgraph.types import interrupt
from workflows.loans.state import LoanState
from workflows.loans.tools import (
    fetch_customer_loans,
    fetch_refinanceable_loans,
    fetch_available_offers,
    DESTRUCTIVE_TOOL_NAMES,
)
from workflows.loans.prompt import SYSTEM_PROMPT_LOANS

logger = logging.getLogger(__name__)


def load_data_node(state: LoanState) -> dict:
    customer_id = state["customer_id"]
    logger.info(f"[loans] Cargando datos para cliente {customer_id}")

    loans = fetch_customer_loans(customer_id)
    refinanceable = fetch_refinanceable_loans(customer_id)
    offers = fetch_available_offers(customer_id)

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
        resumen = (
            f"Estás a punto de refinanciar el préstamo {args['loan_id']}:\n"
            f"- Nuevas cuotas: {args['new_quotas']}\n\n"
            f"¿Confirmás? (sí / no)"
        )
    else:
        resumen = f"¿Confirmás la operación {tool_name}? (sí / no)"

    respuesta = interrupt(resumen)
    confirmed = "sí" in respuesta.lower() or "si" in respuesta.lower()

    logger.info(f"[loans] Confirmación de {tool_name}: {confirmed}")
    return {"confirmed": confirmed}
