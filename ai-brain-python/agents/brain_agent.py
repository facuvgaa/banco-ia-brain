from typing import List, Dict, Any, Union
from agents_config import get_brain_agent
from tools.refinance_tool import _get_refinance_context_impl
from tools.tool_customer_transaction import _get_customer_transactions_impl


class BrainManager:
    def __init__(self) -> None:
        self.model = get_brain_agent()

    def solve_complex_claim(self, claim_text: str, customer_id: str, reason: str) -> Any:
        context_info: str = ""
        
        if customer_id and customer_id != 'UNKNOWN':
            if "REFINANCIACION" in reason.upper() or "PRESTAMO" in reason.upper():
                try:
                    ref_data: Union[Dict[str, Any], str] = _get_refinance_context_impl(customer_id)
                    context_info = f"\n\n[DATOS FINANCIEROS PARA ANÁLISIS]:\n{ref_data}"
                except Exception as e:
                    print(f"⚠️  Error al recuperar ofertas de refinanciación: {e}")
                    context_info = "\n\n⚠️ Error al recuperar ofertas de refinanciación."
            else:
                try:
                    transactions: Union[List[Dict[str, Any]], str] = _get_customer_transactions_impl(customer_id)
                    context_info = f"\n\n[HISTORIAL DE TRANSACCIONES]:\n{self._format_transactions(transactions)}"
                except Exception as e:
                    print(f"⚠️  Error al recuperar historial: {e}")
                    context_info = "\n\n⚠️ Error al recuperar historial."

        messages: List[tuple[str, str]] = [
            ("system", f"Sos el Auditor Senior de un banco en Argentina. Caso: {reason}. "
                       "Tu objetivo es dar una respuesta profesional y clara. "
                       "Si hay datos de refinanciación, compará las tasas de interés. "
                       "Si la tasa nueva es menor, explicá cuánto dinero se ahorra el cliente "
                       "y cuánto es el 'sobrante' que se lleva en mano."),
            ("human", f"ID Cliente: {customer_id}\nConsulta: {claim_text}{context_info}")
        ]

        try:
            return self.model.invoke(messages)
        except ValueError as e:
            error_str: str = str(e)
            if "ThrottlingException" in error_str or "Too many requests" in error_str:
                print(f"❌ Error: Rate limit de AWS Bedrock alcanzado.")
                raise ValueError(f"Rate limit de AWS Bedrock alcanzado. Por favor, espera unos minutos antes de volver a intentar.")
            else:
                print(f"❌ Error de AWS Bedrock: {error_str}")
                raise
        except Exception as e:
            print(f"❌ Error inesperado al invocar AWS Bedrock: {e}")
            raise
    
    def _format_transactions(self, transactions: Union[List[Dict[str, Any]], str]) -> str:
        """Formatea las transacciones para el prompt"""
        if not transactions:
            return "No hay transacciones disponibles."
        
        if isinstance(transactions, str):
            return transactions
        
        if not isinstance(transactions, list):
            return "No hay transacciones disponibles."
        
        formatted: List[str] = []
        for txn in transactions[:10]:
            if isinstance(txn, dict):
                amount: str = str(txn.get('amount', 'N/A'))
                status: str = str(txn.get('status', 'N/A'))
                date: str = str(txn.get('transactionDate', 'N/A'))
                description: str = str(txn.get('description', 'N/A'))
                coelsa_id: str = str(txn.get('coelsaId', 'N/A'))
                formatted.append(f"- {date}: ${amount} ({status}) - {description} [ID: {coelsa_id}]")
        
        return "\n".join(formatted) if formatted else "No hay transacciones disponibles."