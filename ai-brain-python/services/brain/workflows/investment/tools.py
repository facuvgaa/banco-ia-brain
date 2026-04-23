import logging
import os

import httpx

logger = logging.getLogger(__name__)

CORE_API = os.getenv("CORE_API_URL", "http://localhost:8080/api/v1/bank-ia")


def fetch_profile_investor(customer_id: str) -> dict:
    r = httpx.get(f"{CORE_API}/profile-investor/{customer_id}", timeout=15.0)
    r.raise_for_status()
    return r.json()


def delete_profile_investor(customer_id: str) -> None:
    r = httpx.delete(f"{CORE_API}/profile-investor/{customer_id}", timeout=15.0)
    r.raise_for_status()


def save_profile_investor(
    customer_id: str,
    risk_level: str,
    has_profile: bool,
    max_loss_percent: int,
    horizon: str,
) -> dict:
    body = {
        "customerId": customer_id,
        "riskLevel": risk_level,
        "hasProfile": has_profile,
        "maxLossPercent": max_loss_percent,
        "horizon": horizon,
    }
    r = httpx.post(
        f"{CORE_API}/new-profile-investor/{customer_id}",
        json=body,
        timeout=15.0,
    )
    r.raise_for_status()
    return r.json()
