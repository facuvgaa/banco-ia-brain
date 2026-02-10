import time

from agents_config import get_triangle_agent
from schemas.schemas import TriageResult
from agents.brain_agent import BrainManager
from tools.investment_tool import (
    is_investment_session_active,
    get_profile_investor,
    _create_profile_impl,
    _interpret_questionnaire_answer,
    _build_investment_next_step,
    mark_investment_session_active,
    mark_investment_session_complete,
)

# Pausa entre llamada a triage (Haiku) y brain (Sonnet). Son modelos distintos con
# cuotas independientes; 2s es suficiente para no pegarle al mismo endpoint demasiado rápido.
DELAY_BEFORE_SPECIALIST_SECONDS = 2
# Pausa antes de brain cuando el usuario elige opción (2º mensaje). Reducida porque
# el flujo de inversiones ya no hace 2ª llamada Bedrock (early return en Python).
DELAY_BEFORE_CHOICE_BRAIN_SECONDS = 15
# Palabras que indican refinanciación: si el mensaje las tiene, vamos directo al brain (1 llamada Bedrock en vez de 2)
REFINANCE_KEYWORDS = ("refinanciar", "refinance", "prestamos", "préstamos", "prestamo", "préstamo")
REFINANCE_CONTEXT = ("efectivo", "plata", "cuenta", "deudas", "cancelar", "consolidar", "plan")
# El cliente está eligiendo una opción de refinanciación (ej. "la 4", "opción 4", "quiero la opción 4") -> brain
OPTION_CHOICE_PATTERNS = ("opcion", "opción", "la 1", "la 2", "la 3", "la 4", "la 5", "quiero la", "gustaría la", "quiero esa", "esa refinanciacion", "esa refinanciación")


class ResultTriage:
    """Resultado del triage: decisión, motivo y texto de respuesta al usuario."""

    def __init__(
        self,
        decision: str,
        reason: str,
        response_to_user: str,
        category: str = "",
    ) -> None:
        self.decision = decision
        self.reason = reason
        self.response_to_user = response_to_user
        self.category = category


class TriageManager:
    def __init__(self) -> None:
        self.model = get_triangle_agent().with_structured_output(TriageResult)
        self.specialist = BrainManager()

    def _is_clear_refinance(self, text: str) -> bool:
        """Si el mensaje es claramente de refinanciación, no hace falta llamar al triage (ahorramos 1 llamada Bedrock)."""
        t = text.lower().strip()
        has_refinance = any(k in t for k in REFINANCE_KEYWORDS)
        has_context = any(c in t for c in REFINANCE_CONTEXT)
        return has_refinance and (has_context or len(t) > 40)

    def _is_choosing_refinance_option(self, text: str) -> bool:
        """El cliente está eligiendo una opción (ej. 'la 4', 'quiero la opción 4') -> debe ir al brain para ejecutar."""
        t = text.lower().strip()
        if any(p in t for p in OPTION_CHOICE_PATTERNS):
            return True
        # "opcion 4" / "opción 4" con número
        if ("opcion" in t or "opción" in t) and any(str(i) in t for i in range(1, 10)):
            return True
        return False

    def process_chat(
        self,
        text: str,
        customer_id: str,
        claim_id: str = "",
        conversation_history: list[tuple[str, str]] | None = None,
    ) -> ResultTriage:
        _tid = claim_id or "no-claim-id"
        _history = conversation_history or []

        # Fast path: cuestionario de inversión en curso → interpretar en Python (0 LLMs)
        # Cuando el brain hizo la primera pregunta del cuestionario, marcó la sesión
        # como activa. Los siguientes mensajes ("medio", "50%", "1 año") se interpretan
        # directamente en Python con keyword matching, sin llamar a Haiku ni a Sonnet.
        if is_investment_session_active(customer_id):
            profile = get_profile_investor(customer_id)
            parsed = None
            if isinstance(profile, dict):
                parsed = _interpret_questionnaire_answer(text, profile)

            if parsed:
                # Respuesta interpretada → guardar y devolver siguiente pregunta (0 LLMs)
                args = {"customer_id": customer_id, **parsed}
                result = _create_profile_impl(args)
                if isinstance(result, dict):
                    next_step = _build_investment_next_step(result)
                    rl = result.get("riskLevel")
                    ml = result.get("maxLossPercent")
                    hz = result.get("horizon")
                    if rl and ml is not None and hz:
                        mark_investment_session_complete(customer_id)
                    print(f"DEBUG: Inversión: respuesta interpretada en Python (sin LLM) [claim_id={_tid}]")
                    return ResultTriage(
                        decision="ESCALATE",
                        reason="Cuestionario de inversión - respuesta interpretada",
                        response_to_user=next_step,
                        category="INVERSIONES",
                    )

            # Fallback: no se pudo interpretar → usar el brain (Sonnet) con delay
            print(f"DEBUG: Inversión: no se pudo interpretar, escalando al brain [claim_id={_tid}]")
            time.sleep(DELAY_BEFORE_SPECIALIST_SECONDS)
            brain_response = self.specialist.solve_complex_claim(
                claim_text=text,
                customer_id=customer_id,
                reason="Respuesta de cuestionario de inversión",
                category="INVERSIONES",
                claim_id=claim_id,
                conversation_history=_history,
            )
            response_text = (
                brain_response.content
                if hasattr(brain_response, "content")
                else str(brain_response)
            )
            return ResultTriage(
                decision="ESCALATE",
                reason="Cuestionario de inversión en curso",
                response_to_user=response_text,
                category="INVERSIONES",
            )

        # Fast path: refinanciación o elección de opción -> directo al brain
        if self._is_clear_refinance(text):
            print(f"DEBUG: Escalando a especialista por: mensaje de refinanciación (sin triage) [claim_id={_tid}]")
            brain_response = self.specialist.solve_complex_claim(
                claim_text=text,
                customer_id=customer_id,
                reason="Refinanciación de préstamos",
                category="Préstamo",
                claim_id=claim_id,
                conversation_history=_history,
            )
            response_text = (
                brain_response.content
                if hasattr(brain_response, "content")
                else str(brain_response)
            )
            return ResultTriage(
                decision="ESCALATE",
                reason="Refinanciación",
                response_to_user=response_text,
                category="Préstamo",
            )

        # Fast path: cliente elige opción (ej. "la 4", "quiero la opción 4") -> brain debe ejecutar
        if self._is_choosing_refinance_option(text):
            print(f"DEBUG: Escalando a especialista por: elección de opción de refinanciación (sin triage) [claim_id={_tid}]")
            print(f"⏳ Esperando {DELAY_BEFORE_CHOICE_BRAIN_SECONDS}s antes de llamar a Bedrock (evitar rate limit)...")
            time.sleep(DELAY_BEFORE_CHOICE_BRAIN_SECONDS)
            brain_response = self.specialist.solve_complex_claim(
                claim_text=text,
                customer_id=customer_id,
                reason="Refinanciación de préstamos",
                category="Préstamo",
                claim_id=claim_id,
                conversation_history=_history,
            )
            response_text = (
                brain_response.content
                if hasattr(brain_response, "content")
                else str(brain_response)
            )
            return ResultTriage(
                decision="ESCALATE",
                reason="Elección de opción de refinanciación",
                response_to_user=response_text,
                category="Préstamo",
            )

        # Inversiones y resto: pasan por el triage (primer LLM), que escala con INVERSIONES si aplica
        result = self.model.invoke([
            (
                "system",
                "Eres el Triage del banco. Decide si resolver (saludos/info general) o escalar. "
                "Si el usuario quiere invertir, ver bonos, fondos, plazo fijo, dólares o perfil de riesgo: ESCALA (ESCALATE). "
                "Categorías: TRANSFERENCIA, SALDO, PRESTAMO, REFINANCIACION, INVERSIONES.",
            ),
            ("human", text),
        ])

        if result.decision == "RESOLVE":
            return ResultTriage(
                decision=result.decision,
                reason=result.reason,
                response_to_user=result.response_to_user or "",
                category=result.category,
            )

        if result.decision == "ESCALATE":
            print(f"DEBUG: Escalando a especialista por: {result.reason} [claim_id={_tid}]")
            time.sleep(DELAY_BEFORE_SPECIALIST_SECONDS)
            brain_response = self.specialist.solve_complex_claim(
                claim_text=text,
                customer_id=customer_id,
                reason=result.reason,
                category=result.category,
                claim_id=claim_id,
                conversation_history=_history,
            )
            response_text: str = (
                brain_response.content
                if hasattr(brain_response, "content")
                else str(brain_response)
            )
            return ResultTriage(
                decision=result.decision,
                reason=result.reason,
                response_to_user=response_text,
                category=result.category,
            )

        # Fallback por si el modelo devuelve otro valor
        return ResultTriage(
            decision=result.decision,
            reason=result.reason,
            response_to_user=result.response_to_user or "",
            category=result.category,
        )