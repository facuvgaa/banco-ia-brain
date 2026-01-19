from unicodedata import category
from pydantic import BaseModel, Field
from typing import Literal, Optional


class TriageResult(BaseModel):
    decision: Literal["RESOLVE", "ESCALATE"] = Field(description="RESOLVE si es una duda general. ESCALATE si el cliente habla de una transacción, saldo o problema técnico específico."
    )

    category: str = Field(description="Ej: TRANSFERENCIA, SALDO, CUENTA, INFO_GENERAL")
    reason: str = Field(description="Explicación de por qué se tomó esta decisión")
    response_to_user: Optional[str] = Field(description="Respuesta directa al cliente si la decisión fue RESOLVE")