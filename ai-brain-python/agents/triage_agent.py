from agents_config import get_triangle_agent
from schemas import TriageResult 
from agents.brain_agent import BrainManager

class TriageManager:
    def __init__(self):
        self.model = get_triangle_agent().with_structured_output(TriageResult)
        self.specialist = BrainManager() # El agente con acceso a las tools de Java

    def process_chat(self, text: str, customer_id: str) -> str:
        result = self.model.invoke([
            ("system", "Eres el Triage del banco. Analiza si el usuario quiere info general o realizar operaciones (préstamos, refinanciación)."),
            ("human", text)
        ])

        if result.decision == "RESOLVE":
            return result.response_to_user

        if result.decision == "ESCALATE":
            print(f"DEBUG: Escalando a especialista por: {result.reason}")
            return self.specialist.solve_complex_claim(text, customer_id, result.reason)