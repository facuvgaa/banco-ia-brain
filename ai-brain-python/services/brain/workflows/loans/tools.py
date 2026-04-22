import httpx
import os
from uuid import UUID
from langchain_core.tools import tool

CORE_API = os.getenv("CORE_API_URL", "http://localhost:8080/api/v1/bank-ia")


def _norm_uuid(s: str) -> str:
    try:
        return str(UUID(str(s)))
    except (ValueError, TypeError):
        return str(s).strip().lower()


def _tna_of_offer(offer: dict) -> float:
    for k in ("monthlyRate", "annualNominalRate"):
        v = offer.get(k)
        if v is not None:
            return float(v)
    return 0.0


def _find_offer_row(
    offers: list, selected_quotas: int, applied_rate: float
) -> dict | None:
    for o in offers or []:
        if int(o.get("maxQuotas", -1)) != int(selected_quotas):
            continue
        tna = _tna_of_offer(o)
        if abs(tna - float(applied_rate)) < 0.15:
            return o
    return None


# Funciones de lectura - llamadas directamente por nodo_cargar_datos
def fetch_customer_loans(customer_id: str) -> list:
    response = httpx.get(f"{CORE_API}/loans/{customer_id}")
    return response.json()


def fetch_refinanceable_loans(customer_id: str) -> list:
    response = httpx.get(f"{CORE_API}/loans/{customer_id}/to-cancel")
    return response.json()


def fetch_available_offers(customer_id: str) -> list:
    response = httpx.get(f"{CORE_API}/{customer_id}/available-offer")
    return response.json()


# Tools destructivas - el LLM las llama con confirmación previa
@tool
def create_new_loan(customer_id: str, amount: float, quotas: int, rate: float) -> dict:
    """Crea un nuevo préstamo para el cliente con el monto, cuotas y tasa indicados."""
    response = httpx.post(
        f"{CORE_API}/new-loan/{customer_id}",
        json={"amount": amount, "quotas": quotas, "rate": rate}
    )
    return response.json()


@tool
def execute_refinance(
    customer_id: str,
    source_loan_ids: list[str],
    offered_amount: float,
    selected_quotas: int,
    applied_rate: float,
    expected_cash_out: float,
) -> dict:
    """Refinancia uno o varios préstamos activos. Debe alinear cuotas y TNA con una fila de ofertas del cliente.

    - source_loan_ids: UUIDs de préstamos a cancelar (como en el JSON de loans).
    - offered_amount: **no puede superar** el `maxAmount` de la oferta (JSON); debe ser >= suma de saldos refinanciados.
    - selected_quotas / applied_rate: deben coincidir con una oferta (maxQuotas y TNA de esa oferta).
    - expected_cash_out: ≈ offered_amount − suma de saldos; el backend aplica el monto ofrecido validado.
    """
    offers = fetch_available_offers(customer_id)
    row = _find_offer_row(offers, selected_quotas, applied_rate)
    if not row:
        return {
            "ok": False,
            "error": "sin_oferta_compatible",
            "message": (
                "No hay oferta con ese par cuotas/TNA. Revisá `offers`: maxQuotas y TNA "
                "(monthlyRate/annualNominalRate) deben coincidir exactamente con una fila."
            ),
        }

    max_amt = float(row.get("maxAmount", 0) or 0)
    if float(offered_amount) > max_amt + 0.01:
        return {
            "ok": False,
            "error": "monto_sobre_tope",
            "message": (
                f"offered_amount ${offered_amount:,.0f} supera el tope de esta oferta (${max_amt:,.0f}). "
                "Elegí otra oferta con mayor tope, o bajá monto/efectivo en mano."
            ),
            "maxAmount": max_amt,
            "tna": _tna_of_offer(row),
        }

    loans = fetch_customer_loans(customer_id)
    wanted = {_norm_uuid(x) for x in source_loan_ids}
    debt = 0.0
    for l in loans or []:
        lid = l.get("id")
        if _norm_uuid(lid) in wanted:
            ra = l.get("remainingAmount")
            debt += float(ra) if ra is not None else 0.0
    if float(offered_amount) < debt - 0.01:
        return {
            "ok": False,
            "error": "monto_insuficiente",
            "message": f"offered_amount debe cubrir al menos el saldo total refinanciado (~${debt:,.0f}).",
            "deuda_a_cancelar": debt,
        }

    payload = {
        "customerId": customer_id,
        "sourceLoanIds": source_loan_ids,
        "offeredAmount": offered_amount,
        "selectedQuotas": selected_quotas,
        "appliedRate": applied_rate,
        "expectedCashOut": expected_cash_out,
    }
    r = httpx.post(f"{CORE_API}/refinance", json=payload, timeout=60.0)
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text}
    if not r.is_success:
        return {"ok": False, "status_code": r.status_code, "detail": body}
    if isinstance(body, dict) and body.get("success") and isinstance(body.get("data"), dict):
        d = body["data"]
        return {
            "ok": True,
            "mensaje": d.get("message", ""),
            "nuevo_prestamo_numero": d.get("newLoanNumber"),
            "deuda_cancelada": d.get("totalDebtCanceled"),
            "efectivo_acreditado": d.get("cashOut"),
            "tna_aplicada_porciento": d.get("appliedNominalAnnualRate"),
        }
    return body


DESTRUCTIVE_TOOLS = [create_new_loan, execute_refinance]
DESTRUCTIVE_TOOL_NAMES = {t.name for t in DESTRUCTIVE_TOOLS}
