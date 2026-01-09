from agents_config import get_brain_agent

class BrainManager:
    def __init__(self):
        self.model = get_brain_agent()

    
    def solve_complex_claim(self, claim_text, reason):
        prompt = [
            ("system", f"Eres el especialista Senior del banco. El Triage te pasó este caso por: {reason}. "
                       "Analiza el problema con profundidad. Si el usuario menciona transacciones, "
                       "dile que estás iniciando la auditoría de su cuenta."),
            ("human", claim_text)
        ]
        return self.model.invoke(prompt)