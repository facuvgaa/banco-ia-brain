from agents_config import get_brain_agent
from tools import get_customer_transactions


class BrainManager:
    def __init__(self):
        self.model = get_brain_agent()
        self.tools = [get_customer_transactions]
        self.model_with_tools = self.model.bind_tools(self.tools)

    
    def solve_complex_claim(self, claim_text,customer_id, reason):
        prompt = [
            ("system", f"""Eres el Auditor Senior de Reclamos del Banco. 
            El caso ha sido escalado por el Triage debido a: {reason}.
            
            REGLAS CRÍTICAS:
            1. Antes de dar cualquier respuesta final sobre dinero, DEBES usar la herramienta 'get_customer_transactions' para verificar la realidad en el sistema.
            2. Si ves una transacción 'PENDING' o 'FAILED', explícale al cliente el motivo técnico.
            3. Tu tono debe ser profesional, empático y basado estrictamente en los datos que obtengas del sistema.
            4. Si los datos no coinciden con lo que dice el cliente, indícalo con respeto."""),
            
            ("human", f"ID de Cliente: {customer_id}\nReclamo del Cliente: {claim_text}")
        ]
        return self.model_with_tools.invoke(prompt)