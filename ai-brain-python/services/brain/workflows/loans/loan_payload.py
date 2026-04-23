"""
Normaliza JSON de préstamos y ofertas (keys camelCase) para el LLM.
Evita TNA "—" cuando el dato existe con otro nombre o falta mapeo.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, List


def _fnum(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def enrich_loan_row(loan: dict) -> dict:
    d = deepcopy(loan) if loan else {}
    tna = _fnum(
        d.get("nominalAnnualRate")
        or d.get("nominal_annual_rate")
    )
    if tna is not None:
        d["tnaAnualPorciento"] = tna
        d["tnaDisplay"] = f"{tna:g}% TNA" if tna == int(tna) else f"{tna:.1f}% TNA"
    else:
        d["tnaAnualPorciento"] = None
        d["tnaDisplay"] = None
    return d


def enrich_loans_list(loans: list | None) -> List[dict]:
    if not loans:
        return []
    return [enrich_loan_row(x) for x in loans if isinstance(x, dict)]


def enrich_offer_row(offer: dict) -> dict:
    d = deepcopy(offer) if offer else {}
    # En este backend annualNominalRate y monthlyRate duplican el mismo TNA anual
    tna = _fnum(
        d.get("annualNominalRate")
        or d.get("annual_nominal_rate")
        or d.get("monthlyRate")
        or d.get("monthly_rate")
    )
    if tna is not None:
        d["tnaAnualPorciento"] = tna
        d["tnaDisplay"] = f"{tna:g}% TNA" if tna == int(tna) else f"{tna:.1f}% TNA"
    return d


def enrich_offers_list(offers: list | None) -> List[dict]:
    if not offers:
        return []
    return [enrich_offer_row(x) for x in offers if isinstance(x, dict)]
