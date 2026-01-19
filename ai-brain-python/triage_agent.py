from agents_config import get_triangle_agent
from schemas import TriageResult 

class TriageManager:
    def __init__(self):
        self.model = get_triangle_agent().with_structured_output(TriageResult)

    def process_claim(self, text):
        prompt = [
            ("system", "Eres el Triage de un banco. Analiza el reclamo. "
                       "Si es una duda general, responde (RESOLVE). "
                       "Si implica dinero o transacciones, escala (ESCALATE)."),
            ("human", text)
        ]
        return self.model.invoke(prompt)