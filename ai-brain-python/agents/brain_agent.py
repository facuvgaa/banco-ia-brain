from agents_config import get_brain_agent
from tools import _get_customer_transactions_impl


class BrainManager:
    def __init__(self):
        self.model = get_brain_agent()

    def solve_complex_claim(self, claim_text, customer_id, reason):
        """
        Arquitectura optimizada: Obtiene transacciones directamente y hace UNA sola llamada al modelo.
        Esto reduce las llamadas a Bedrock de 2 a 1.
        """
        # Obtener transacciones directamente si tenemos customer_id válido
        transactions_info = ""
        if customer_id and customer_id != 'UNKNOWN':
            try:
                transactions = _get_customer_transactions_impl(customer_id)
                if transactions and isinstance(transactions, list):
                    transactions_info = f"\n\nHistorial de Transacciones del Cliente:\n{self._format_transactions(transactions)}"
                elif isinstance(transactions, str):
                    transactions_info = f"\n\n{transactions}"
            except Exception as e:
                print(f"⚠️  No se pudieron obtener transacciones: {e}")
                transactions_info = "\n\nNota: No se pudieron obtener las transacciones del cliente."

        # Una sola llamada al modelo con toda la información
        messages = [
            ("system", f"Eres el Auditor Senior de Reclamos de un Banco Argentino. "
                      f"Caso escalado por: {reason}. "
                      f"Analiza el reclamo y las transacciones proporcionadas para dar una respuesta completa."),
            ("human", f"ID de Cliente: {customer_id}\nReclamo: {claim_text}{transactions_info}")
        ]

        try:
            response = self.model.invoke(messages)
            return response
            
        except ValueError as e:
            error_str = str(e)
            if "ThrottlingException" in error_str or "Too many requests" in error_str:
                print(f"❌ Error: Rate limit de AWS Bedrock alcanzado.")
                raise ValueError(f"Rate limit de AWS Bedrock alcanzado. Por favor, espera unos minutos antes de volver a intentar.")
            else:
                print(f"❌ Error de AWS Bedrock: {error_str}")
                raise
        except Exception as e:
            print(f"❌ Error inesperado al invocar AWS Bedrock: {e}")
            raise
    
    def _format_transactions(self, transactions):
        """Formatea las transacciones para el prompt"""
        if not transactions:
            return "No hay transacciones disponibles."
        
        formatted = []
        for txn in transactions[:10]:  # Limitar a 10 transacciones más recientes
            if isinstance(txn, dict):
                amount = txn.get('amount', 'N/A')
                status = txn.get('status', 'N/A')
                date = txn.get('transactionDate', 'N/A')
                description = txn.get('description', 'N/A')
                coelsa_id = txn.get('coelsaId', 'N/A')
                formatted.append(f"- {date}: ${amount} ({status}) - {description} [ID: {coelsa_id}]")
        
        return "\n".join(formatted) if formatted else "No hay transacciones disponibles."