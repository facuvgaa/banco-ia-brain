import time
from typing import Any, Dict, List
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
from prompts.promptBrain import get_system_prompt
import logging

logging.basicConfig(filename='brain_agent.log', level=logging.DEBUG)
logger = logging.getLogger(__name__)



class BrainManager:
    def __init__(self) -> None:
        self.model = get_brain_agent()
        # Solo bind execute_refinance, ya que get_refinance_context lo obtenemos antes
        self.model_with_tools = self.model.bind_tools([execute_refinance])
        # Cache simple para respuestas (TTL de 5 minutos)
        self._response_cache: Dict[str, tuple[Any, float]] = {}
        self._cache_ttl: float = 300.0  

    def solve_complex_claim(self, claim_text: str, customer_id: str, reason: str, category: str) -> Any:
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
                logging.debug(f"💾 DEBUG: Usando respuesta cacheada")
                return cached_response
            
            time.sleep(0.5)
            # Una sola llamada: botocore ya hace hasta 5 reintentos con backoff; retry propio multiplicaba (3×5=15) requests
            response = self.model_with_tools.invoke(messages)
            logging.debug(f"🔍 DEBUG: Tipo de respuesta: {type(response)}")
            logging.debug(f"🔍 DEBUG: Contenido de respuesta: {response.content if hasattr(response, 'content') else str(response)[:200]}")
            
            # Verificar si el modelo quiere ejecutar una tool
            tool_calls = getattr(response, 'tool_calls', None) or []
            logging.debug(f"🔍 DEBUG: Tool calls encontradas: {len(tool_calls)}")
            
            # Cachear respuesta si no tiene tool calls
            if not tool_calls:
                self._response_cache[cache_key] = (response, time.time())
            
            if tool_calls:
                logging.debug(f"🔧 DEBUG: Modelo quiere ejecutar {len(tool_calls)} tool(s)")
                
                # Construir mensajes para el siguiente paso
                current_messages = list(messages)
                current_messages.append(response)
                
                # Ejecutar cada tool call
                tool_results = []
                for i, tool_call in enumerate(tool_calls):
                    try:
                        tool_name = getattr(tool_call, 'name', None) or (tool_call.get('name', '') if isinstance(tool_call, dict) else '')
                        logging.debug(f"🔧 DEBUG [{i+1}/{len(tool_calls)}]: Ejecutando tool: {tool_name}")
                        
                        # Extraer argumentos de la tool call
                        if hasattr(tool_call, "args"):
                            raw_args = tool_call.args
                        elif isinstance(tool_call, dict):
                            raw_args = tool_call.get("args", {})
                        else:
                            raw_args = {}
                        logging.debug(f"🔍 DEBUG: Args de tool: {raw_args}")

                        eligible_loan_ids = get_eligible_loan_ids(ctx, customer_id)

                        args = normalize_execute_refinance_args(
                            raw_args,
                            customer_id,
                            loan_number_to_id_map,
                            eligible_loan_ids,
                        )
                        logging.debug(f"✅ DEBUG: Payload normalizado: sourceLoanIds={args.get('sourceLoanIds', [])}")

                        # Ejecutar la tool correspondiente
                        if tool_name == "execute_refinance":
                            logging.debug(f"🔧 DEBUG: Ejecutando refinanciación para {customer_id}")
                            logging.debug(f"🔍 DEBUG: Payload final: {args}")
                            result = _execute_refinance_impl(args)
                            logging.debug(f"✅ Resultado de refinanciación: {result}")
                            result_str = str(result).lower()
                            
                            # Si la refinanciación fue exitosa, generar respuesta directamente sin invocar el modelo
                            if "éxito" in result_str or "exitoso" in result_str or "success" in result_str or "procesada" in result_str:
                                logging.debug("✅ Refinanciación exitosa, generando respuesta directa sin invocar modelo")
                                amount_credited = args.get("expectedCashOut", 0)
                                message = refinance_success_message(customer_id, amount_credited)
                                from langchain_core.messages import AIMessage
                                return AIMessage(content=message)
                            
                            tool_results.append(str(result))
                        else:
                            logging.debug(f"⚠️  Tool desconocida: {tool_name}")
                            tool_results.append(f"Tool {tool_name} no reconocida")
                    except Exception as tool_error:
                        logging.debug(f"❌ Error ejecutando tool {i+1}: {tool_error}")
                        import traceback
                        logging.debug(traceback.print_exc())
                        tool_results.append(f"Error ejecutando tool: {str(tool_error)}")
                
                # Agregar resultados de tools y obtener respuesta final
                for result in tool_results:
                    current_messages.append(("human", f"Resultado de la herramienta: {result}"))
                
                logging.debug(f"🔍 DEBUG: Invocando modelo con {len(current_messages)} mensajes")
                time.sleep(0.5)
                final_response = self.model_with_tools.invoke(current_messages)
                logging.debug(f"✅ DEBUG: Respuesta final obtenida")
                return final_response
            
            return response
        except ValueError as e:
            error_str: str = str(e)
            if "ThrottlingException" in error_str or "Too many requests" in error_str:
                logging.debug(f"❌ Error: Rate limit de AWS Bedrock alcanzado.")
                raise ValueError(f"Rate limit de AWS Bedrock alcanzado. Por favor, espera unos minutos antes de volver a intentar.")
            else:
                logging.debug(f"❌ Error de AWS Bedrock: {error_str}")
                raise
        except Exception as e:
            logging.debug(f"❌ Error inesperado al invocar AWS Bedrock: {e}")
            raise
    