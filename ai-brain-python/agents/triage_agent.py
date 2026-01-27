from agents_config import get_triangle_agent
from schemas import TriageResult 
from agents.brain_agent import BrainManager

class TriageManager:
    def __init__(self):
        self.model = get_triangle_agent().with_structured_output(TriageResult)
        self.specialist = BrainManager() 

    def process_chat(self, text: str, customer_id: str) -> str:
        result = self.model.invoke([
            ("system", "Eres el Triage del banco. Decide si resolver (saludos/info general) o escalar."),
            ("human", text)
        ])

        if result.decision == "RESOLVE":
            return result.response_to_user

        if result.decision == "ESCALATE":
            print(f"DEBUG: Escalando a especialista por: {result.reason}")
            brain_response = self.specialist.solve_complex_claim(
                claim_text=text, 
                customer_id=customer_id, 
                reason=f"{result.category} - {result.reason}"
            )
            return brain_response.content if hasattr(brain_response, 'content') else str(brain_response)