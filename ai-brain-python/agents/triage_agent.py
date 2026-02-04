import time

from agents_config import get_triangle_agent
from schemas.schemas import TriageResult
from agents.brain_agent import BrainManager

# Pausa entre llamada a triage y brain cuando SÍ usamos triage (evitar throttling)
DELAY_BEFORE_SPECIALIST_SECONDS = 5
# Pausa antes de brain cuando el usuario elige opción (2º mensaje). Bedrock aplica RPM
# (requests/min); 45s suele bastar si la cuota no es 1 RPM estricto.
DELAY_BEFORE_CHOICE_BRAIN_SECONDS = 45

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

    def process_chat(self, text: str, customer_id: str, claim_id: str = "") -> ResultTriage:
        _tid = claim_id or "no-claim-id"
        # Fast path: refinanciación o elección de opción -> directo al brain
        if self._is_clear_refinance(text):
            print(f"DEBUG: Escalando a especialista por: mensaje de refinanciación (sin triage) [claim_id={_tid}]")
            brain_response = self.specialist.solve_complex_claim(
                claim_text=text,
                customer_id=customer_id,
                reason="Refinanciación de préstamos",
                category="Préstamo",
                claim_id=claim_id,
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

        result = self.model.invoke([
            ("system", "Eres el Triage del banco. Decide si resolver (saludos/info general) o escalar."),
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