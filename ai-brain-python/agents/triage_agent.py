from agents_config import get_triangle_agent
from schemas.schemas import TriageResult
from agents.brain_agent import BrainManager


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

    def process_chat(self, text: str, customer_id: str) -> ResultTriage:
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
            print(f"DEBUG: Escalando a especialista por: {result.reason}")
            brain_response = self.specialist.solve_complex_claim(
                claim_text=text,
                customer_id=customer_id,
                reason=result.reason,
                category=result.category,
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