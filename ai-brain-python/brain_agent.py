from agents_config import get_brain_agent
from tools import get_customer_transactions


class BrainManager:
    def __init__(self):
        self.model = get_brain_agent()
        self.tools = [get_customer_transactions]
        self.model_with_tools = self.model.bind_tools(self.tools)

    
    def solve_complex_claim(self, claim_text,customer_id, reason):
        prompt = [
            ("system", """Eres el Auditor Senior de Reclamos Bancarios en Argentina.
        
            REGLA DE ORO COELSA:
            1. Si el cliente reclama por una transferencia que no llegó, DEBES buscar el 'coelsaId' en el sistema.
            2. Si el 'status' es FAILED pero existe un 'coelsaId', significa que la plata salió hacia COELSA. Dile al cliente: 
            'La transferencia cuenta con código COELSA {coelsaId}. Por favor, aguarde 72hs hábiles.'
            3. Si NO existe 'coelsaId', el error es interno nuestro y debemos devolver la plata de inmediato."""),
        
            ("human", f"ID de Cliente: {customer_id}\nReclamo: {claim_text}\nCoelsa ID: {reason}")
            ]
        return self.model_with_tools.invoke(prompt)