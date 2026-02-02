import time
from typing import Any, Dict, List

from agents_config import get_brain_agent
from contexts.context_builder import build_context
from tools.refinance_tool import (
    _execute_refinance_impl,
    _get_refinance_context_impl,
    execute_refinance,
    get_refinance_context,
    normalize_execute_refinance_args,
)
from prompts.promptBrain import get_system_prompt

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
        ref_data = ctx.ref_data
        loan_number_to_id_map = ctx.loan_number_to_id_map
        eligible_loans_list = ctx.eligible_loans_list

        # Preparar el mensaje del sistema
        system_prompt = get_system_prompt(customer_id, reason, category)

        messages: List[tuple[str, str]] = [
            ("system", system_prompt),
            ("human", f"ID Cliente: {customer_id}\nConsulta: {claim_text}{context_info}")
        ]

        try:
            cache_key = f"{customer_id}:{claim_text[:50]}"
            cached_response, cache_time = self._response_cache.get(cache_key, (None, 0))
            if cached_response and (time.time() - cache_time) < self._cache_ttl:
                print(f"💾 DEBUG: Usando respuesta cacheada")
                return cached_response
            
            time.sleep(0.5)
            
            response = self._invoke_with_retry(messages)
            print(f"🔍 DEBUG: Tipo de respuesta: {type(response)}")
            print(f"🔍 DEBUG: Contenido de respuesta: {response.content if hasattr(response, 'content') else str(response)[:200]}")
            
            # Verificar si el modelo quiere ejecutar una tool
            tool_calls = getattr(response, 'tool_calls', None) or []
            print(f"🔍 DEBUG: Tool calls encontradas: {len(tool_calls)}")
            
            # Cachear respuesta si no tiene tool calls
            if not tool_calls:
                self._response_cache[cache_key] = (response, time.time())
            
            if tool_calls:
                print(f"🔧 DEBUG: Modelo quiere ejecutar {len(tool_calls)} tool(s)")
                
                # Construir mensajes para el siguiente paso
                current_messages = list(messages)
                current_messages.append(response)
                
                # Ejecutar cada tool call
                tool_results = []
                for i, tool_call in enumerate(tool_calls):
                    try:
                        tool_name = getattr(tool_call, 'name', None) or (tool_call.get('name', '') if isinstance(tool_call, dict) else '')
                        print(f"🔧 DEBUG [{i+1}/{len(tool_calls)}]: Ejecutando tool: {tool_name}")
                        
                        # Extraer argumentos de la tool call
                        if hasattr(tool_call, "args"):
                            raw_args = tool_call.args
                        elif isinstance(tool_call, dict):
                            raw_args = tool_call.get("args", {})
                        else:
                            raw_args = {}
                        print(f"🔍 DEBUG: Args de tool: {raw_args}")

                        # Construir lista de UUIDs elegibles (contexto o API)
                        eligible_loans_from_data = []
                        if isinstance(ref_data, dict):
                            eligible_loans_from_data = ref_data.get("eligible_loans", [])
                        if not eligible_loans_from_data and eligible_loans_list:
                            eligible_loans_from_data = eligible_loans_list
                        if not eligible_loans_from_data:
                            try:
                                fresh = _get_refinance_context_impl(customer_id)
                                if isinstance(fresh, dict):
                                    eligible_loans_from_data = fresh.get("eligible_loans", [])
                            except Exception:
                                pass
                        eligible_loan_ids = [
                            str(loan.get("id", ""))
                            for loan in eligible_loans_from_data
                            if isinstance(loan, dict) and loan.get("id")
                        ]

                        args = normalize_execute_refinance_args(
                            raw_args,
                            customer_id,
                            loan_number_to_id_map,
                            eligible_loan_ids,
                        )
                        print(f"✅ DEBUG: Payload normalizado: sourceLoanIds={args.get('sourceLoanIds', [])}")

                        # Ejecutar la tool correspondiente
                        if tool_name == "execute_refinance":
                            print(f"🔧 DEBUG: Ejecutando refinanciación para {customer_id}")
                            print(f"🔍 DEBUG: Payload final: {args}")
                            result = _execute_refinance_impl(args)
                            print(f"✅ Resultado de refinanciación: {result}")
                            result_str = str(result).lower()
                            
                            # Si la refinanciación fue exitosa, generar respuesta directamente sin invocar el modelo
                            if "éxito" in result_str or "exitoso" in result_str or "success" in result_str or "procesada" in result_str:
                                print(f"✅ Refinanciación exitosa, generando respuesta directa sin invocar modelo")
                                expected_cash_out = args.get('expectedCashOut', 0)
                                success_message = (
                                    f"¡Excelente, {customer_id}! La refinanciación se ha completado exitosamente. "
                                    f"Todos tus préstamos han sido consolidados en un nuevo préstamo y el dinero sobrante "
                                    f"(${expected_cash_out:,.2f}) ha sido acreditado a tu cuenta. "
                                    f"Podés verificar el nuevo préstamo y el saldo actualizado en tu cuenta."
                                )
                                # Retornar directamente sin invocar el modelo
                                from langchain_core.messages import AIMessage
                                return AIMessage(content=success_message)
                            
                            tool_results.append(str(result))
                        else:
                            print(f"⚠️  Tool desconocida: {tool_name}")
                            tool_results.append(f"Tool {tool_name} no reconocida")
                    except Exception as tool_error:
                        print(f"❌ Error ejecutando tool {i+1}: {tool_error}")
                        import traceback
                        traceback.print_exc()
                        tool_results.append(f"Error ejecutando tool: {str(tool_error)}")
                
                # Agregar resultados de tools y obtener respuesta final
                for result in tool_results:
                    current_messages.append(("human", f"Resultado de la herramienta: {result}"))
                
                print(f"🔍 DEBUG: Invocando modelo con {len(current_messages)} mensajes")
                # Delay antes de la segunda llamada
                time.sleep(0.5)
                final_response = self._invoke_with_retry(current_messages)
                print(f"✅ DEBUG: Respuesta final obtenida")
                return final_response
            
            return response
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
    
    def _invoke_with_retry(self, messages: List[tuple[str, str]], max_retries: int = 3) -> Any:
        """
        Invoca el modelo con retry y backoff exponencial para manejar rate limits.
        """
        base_delay = 2.0  # Delay inicial de 2 segundos
        
        for attempt in range(max_retries):
            try:
                return self.model_with_tools.invoke(messages)
            except ValueError as e:
                error_str = str(e)
                if "ThrottlingException" in error_str or "Too many requests" in error_str:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # Backoff exponencial: 2s, 4s, 8s
                        print(f"⏳ Rate limit alcanzado. Reintentando en {delay:.1f} segundos... (intento {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"❌ Error: Rate limit de AWS Bedrock alcanzado después de {max_retries} intentos.")
                        raise ValueError(f"Rate limit de AWS Bedrock alcanzado. Por favor, espera unos minutos antes de volver a intentar.")
                else:
                    # Otro tipo de ValueError, re-lanzar
                    raise
            except Exception as e:
                # Para otros errores, re-lanzar inmediatamente
                raise
        
        # Esto no debería ejecutarse nunca, pero por si acaso
        raise Exception("Error inesperado en _invoke_with_retry")