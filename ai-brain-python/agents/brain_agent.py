import time
from typing import Any, Dict, List
from botocore.exceptions import ClientError
from agents_config import get_brain_agent
from contexts.context_builder import (
    build_context,
    get_eligible_loan_ids,
    refinance_success_message,
)


from tools.refinance_tool import (
    _execute_refinance_impl,
    execute_refinance,
    get_refinance_context,
    normalize_execute_refinance_args,
)

from tools.newLoan import (
    OfferLoan,
    execute_new_loan,
    _execute_new_loan_impl,
    normalize_new_loan_args
)

from prompts.promptBrain import get_system_prompt
import logging

logging.basicConfig(filename='brain_agent.log', level=logging.DEBUG)
logger = logging.getLogger(__name__)



class BrainManager:
    def __init__(self) -> None:
        self.model = get_brain_agent()
        self.model_with_tools = self.model.bind_tools([execute_refinance, execute_new_loan])
        # Cache simple para respuestas (TTL de 5 minutos)
        self._response_cache: Dict[str, tuple[Any, float]] = {}
        self._cache_ttl: float = 300.0  

    def solve_complex_claim(
        self,
        claim_text: str,
        customer_id: str,
        reason: str,
        category: str,
        claim_id: str = "",
    ) -> Any:
        _tid = claim_id or "no-claim-id"
        logging.debug(f"[claim_id={_tid}] solve_complex_claim inicio customer_id={customer_id} reason={reason}")
        ctx = build_context(customer_id, reason, category)
        context_info = ctx.context_info
        loan_number_to_id_map = ctx.loan_number_to_id_map

        # Preparar el mensaje del sistema (inyectamos números de la mejor oferta si hay)
        system_prompt = get_system_prompt(
            customer_id, reason, category, getattr(ctx, "best_offer_summary", None) or {}
        )

        messages: List[tuple[str, str]] = [
            ("system", system_prompt),
            ("human", f"ID Cliente: {customer_id}\nConsulta: {claim_text}{context_info}")
        ]

        try:
            cache_key = f"{customer_id}:{claim_text[:50]}"
            cached_response, cache_time = self._response_cache.get(cache_key, (None, 0))
            if cached_response and (time.time() - cache_time) < self._cache_ttl:
                logging.debug(f"[claim_id={_tid}] 💾 Usando respuesta cacheada")
                return cached_response
            
            time.sleep(0.5)
            logging.debug(f"[claim_id={_tid}] INVOKE_START (1ª llamada Bedrock)")
            response = self.model_with_tools.invoke(messages)
            logging.debug(f"[claim_id={_tid}] INVOKE_END (1ª llamada Bedrock)")
            logging.debug(f"[claim_id={_tid}] 🔍 Tipo de respuesta: {type(response)}")
            logging.debug(f"[claim_id={_tid}] 🔍 Contenido: {response.content if hasattr(response, 'content') else str(response)[:200]}")
            
            # Verificar si el modelo quiere ejecutar una tool
            tool_calls = getattr(response, 'tool_calls', None) or []
            logging.debug(f"[claim_id={_tid}] 🔍 Tool calls: {len(tool_calls)}")
            
            # Cachear respuesta si no tiene tool calls
            if not tool_calls:
                self._response_cache[cache_key] = (response, time.time())
            
            if tool_calls:
                logging.debug(f"[claim_id={_tid}] 🔧 Modelo quiere ejecutar {len(tool_calls)} tool(s)")
                
                # Construir mensajes para el siguiente paso
                current_messages = list(messages)
                current_messages.append(response)
                
                # Ejecutar cada tool call
                tool_results = []
                for i, tool_call in enumerate(tool_calls):
                    try:
                        tool_name = getattr(tool_call, 'name', None) or (tool_call.get('name', '') if isinstance(tool_call, dict) else '')
                        logging.debug(f"[claim_id={_tid}] 🔧 Ejecutando tool [{i+1}/{len(tool_calls)}]: {tool_name}")
                        
                        # Extraer argumentos de la tool call
                        if hasattr(tool_call, "args"):
                            raw_args = tool_call.args
                        elif isinstance(tool_call, dict):
                            raw_args = tool_call.get("args", {})
                        else:
                            raw_args = {}
                        logging.debug(f"[claim_id={_tid}] 🔍 Args de tool: {raw_args}")

                        if tool_name == "execute_refinance":
                            eligible_loan_ids = get_eligible_loan_ids(ctx, customer_id)
                            args = normalize_execute_refinance_args(
                                raw_args,
                                customer_id,
                                loan_number_to_id_map,
                                eligible_loan_ids,
                            )
                            logging.debug(f"[claim_id={_tid}] ✅ Payload normalizado: sourceLoanIds={args.get('sourceLoanIds', [])}")
                            logging.debug(f"[claim_id={_tid}] 🔧 Ejecutando refinanciación customer_id={customer_id}")
                            result = _execute_refinance_impl(args)
                            logging.debug(f"[claim_id={_tid}] ✅ Resultado refinanciación: {result}")
                            result_str = str(result).lower()
                            if "éxito" in result_str or "exitoso" in result_str or "success" in result_str or "procesada" in result_str:
                                logging.debug(f"[claim_id={_tid}] ✅ Refinanciación exitosa, respuesta directa")
                                amount_credited = args.get("expectedCashOut", 0)
                                message = refinance_success_message(customer_id, amount_credited)
                                from langchain_core.messages import AIMessage
                                return AIMessage(content=message)
                            tool_results.append(str(result))
                        elif tool_name == "execute_new_loan":
                            args = normalize_new_loan_args(raw_args, customer_id)
                            logging.debug(f"[claim_id={_tid}] ✅ Payload new loan: amount={args.get('amount')}, quotas={args.get('quotas')}, rate={args.get('rate')}")
                            logging.debug(f"[claim_id={_tid}] 🔧 Ejecutando nuevo préstamo customer_id={customer_id}")
                            result = _execute_new_loan_impl(args)
                            logging.debug(f"[claim_id={_tid}] ✅ Resultado nuevo préstamo: {result}")
                            result_str = str(result).lower()
                            if "éxito" in result_str or "creado" in result_str:
                                logging.debug(f"[claim_id={_tid}] ✅ Nuevo préstamo exitoso, respuesta directa")
                                from langchain_core.messages import AIMessage
                                return AIMessage(content="Tu nuevo préstamo fue creado y el monto fue acreditado en tu cuenta.")
                            tool_results.append(str(result))
                        else:
                            logging.debug(f"[claim_id={_tid}] ⚠️ Tool desconocida: {tool_name}")
                            tool_results.append(f"Tool {tool_name} no reconocida")
                    except Exception as tool_error:
                        logging.debug(f"[claim_id={_tid}] ❌ Error ejecutando tool {i+1}: {tool_error}")
                        import traceback
                        logging.debug(f"[claim_id={_tid}] " + str(traceback.format_exc()))
                        tool_results.append(f"Error ejecutando tool: {str(tool_error)}")
                
                # Agregar resultados de tools y obtener respuesta final
                for result in tool_results:
                    current_messages.append(("human", f"Resultado de la herramienta: {result}"))
                
                logging.debug(f"[claim_id={_tid}] INVOKE_START (2ª llamada Bedrock, post-tool)")
                time.sleep(0.5)
                final_response = self.model_with_tools.invoke(current_messages)
                logging.debug(f"[claim_id={_tid}] INVOKE_END (2ª llamada Bedrock)")
                logging.debug(f"[claim_id={_tid}] ✅ Respuesta final obtenida")
                return final_response
            
            return response
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "ThrottlingException" or "ThrottlingException" in str(e):
                logging.debug(f"[claim_id={_tid}] ❌ Rate limit AWS Bedrock (ClientError).")
                raise ValueError(
                    "Rate limit de AWS Bedrock alcanzado. Por favor, espera unos minutos antes de volver a intentar."
                ) from e
            logging.debug(f"[claim_id={_tid}] ❌ ClientError AWS Bedrock: {e}")
            raise
        except ValueError as e:
            error_str: str = str(e)
            if "ThrottlingException" in error_str or "Too many requests" in error_str:
                logging.debug(f"[claim_id={_tid}] ❌ Rate limit AWS Bedrock.")
                raise ValueError(
                    "Rate limit de AWS Bedrock alcanzado. Por favor, espera unos minutos antes de volver a intentar."
                ) from e
            logging.debug(f"[claim_id={_tid}] ❌ Error AWS Bedrock: {error_str}")
            raise
        except Exception as e:
            error_str = str(e)
            if "ThrottlingException" in error_str or "429" in error_str or "Too many requests" in error_str:
                logging.debug(f"[claim_id={_tid}] ❌ Rate limit AWS Bedrock (wrapped).")
                raise ValueError(
                    "Rate limit de AWS Bedrock alcanzado. Por favor, espera unos minutos antes de volver a intentar."
                ) from e
            logging.debug(f"[claim_id={_tid}] ❌ Error inesperado AWS Bedrock: {e}")
            raise
    