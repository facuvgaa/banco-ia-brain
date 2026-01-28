from typing import List, Dict, Any, Union
from agents_config import get_brain_agent
from tools.refinance_tool import _get_refinance_context_impl
from tools.tool_customer_transaction import _get_customer_transactions_impl


class BrainManager:
    def __init__(self) -> None:
        self.model = get_brain_agent()

    def solve_complex_claim(self, claim_text: str, customer_id: str, reason: str, category: str) -> Any:
        context_info: str = ""
        
        # Normalizamos para que "Préstamo", "prestamo" o "PRESTAMO" funcionen igual
        search_text: str = (reason + " " + category).upper()
        search_text = search_text.translate(str.maketrans("ÁÉÍÓÚ", "AEIOU"))

        if customer_id and customer_id != 'UNKNOWN':
            if any(word in search_text for word in ["PRESTAMO", "REFINANCIACION", "DEUDA"]):
                print(f"🚀 DEBUG: Entrando a lógica de PRESTAMOS para {customer_id}")
                try:
                    ref_data: Union[Dict[str, Any], str] = _get_refinance_context_impl(customer_id)
                    if isinstance(ref_data, dict):
                        eligible_loans = ref_data.get("eligible_loans", [])
                        new_offers = ref_data.get("new_offers", [])
                        context_info = f"\n\n[DATOS FINANCIEROS REALES]:\n"
                        context_info += f"Préstamos elegibles para refinanciar: {len(eligible_loans)}\n"
                        if eligible_loans:
                            for loan in eligible_loans:
                                if isinstance(loan, dict):
                                    context_info += f"- Préstamo {loan.get('loanNumber', 'N/A')}: ${loan.get('remainingAmount', 0)} restantes ({loan.get('paidQuotas', 0)}/{loan.get('totalQuotas', 0)} cuotas pagadas)\n"
                        context_info += f"\nOfertas nuevas disponibles: {len(new_offers)}\n"
                        if new_offers:
                            for offer in new_offers:
                                if isinstance(offer, dict):
                                    context_info += f"- Oferta: ${offer.get('maxAmount', 0)} máximo, {offer.get('maxQuotas', 0)} cuotas, tasa {offer.get('monthlyRate', 0)}%\n"
                    else:
                        context_info = f"\n\n[DATOS FINANCIEROS REALES]:\n{ref_data}"
                except Exception as e:
                    print(f"⚠️  Error consultando deudas: {e}")
                    import traceback
                    traceback.print_exc()
                    context_info = "\n\nError consultando deudas."
            else:
                # Caso estándar de transacciones
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