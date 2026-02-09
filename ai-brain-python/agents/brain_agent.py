import json
import time
from typing import Any, Dict, List, Optional
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

from tools.investment_tool import (
    get_risk_profile,
    create_or_update_profile_investor,
    get_profile_investor,
    _create_profile_impl,
    mark_investment_session_active,
    mark_investment_session_complete,
    _build_investment_next_step,
)

from prompts.promptBrain import get_system_prompt
from langchain_core.messages import AIMessage, ToolMessage
import logging

logging.basicConfig(filename='brain_agent.log', level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Pausa antes de la 2ª llamada a Bedrock (post-tool) para flujos NO-inversiones.
DELAY_BEFORE_SECOND_INVOKE_SECONDS = 15
# Si Bedrock devuelve rate limit, esperar este tiempo y reintentar una vez.
RETRY_AFTER_THROTTLE_SECONDS = 60


class BrainManager:
    def __init__(self) -> None:
        self.model = get_brain_agent()
        self.model_with_tools = self.model.bind_tools([execute_refinance, execute_new_loan, get_risk_profile, create_or_update_profile_investor])
        # Cache simple para respuestas (TTL de 5 minutos)
        self._response_cache: Dict[str, tuple[Any, float]] = {}
        self._cache_ttl: float = 300.0

    def _is_throttle_error(self, e: BaseException) -> bool:
        """LangChain envuelve ClientError de Bedrock en ValueError; detectamos throttle por mensaje o causa."""
        msg = str(e).lower()
        if "throttl" in msg or "429" in msg or "rate limit" in msg or "too many requests" in msg:
            return True
        if isinstance(e, ClientError):
            code = e.response.get("Error", {}).get("Code", "")
            return code == "ThrottlingException"
        # LangChain wrap: ValueError con __cause__ = ClientError(ThrottlingException)
        if isinstance(e, ValueError):
            cause = getattr(e, "__cause__", None)
            if cause is not None:
                return self._is_throttle_error(cause)
        return False

    def _invoke_with_retry(self, messages, label: str = ""):
        """Llama a Bedrock; si devuelve ThrottlingException (o ValueError envuelto por LangChain), espera y reintenta una vez."""
        try:
            return self.model_with_tools.invoke(messages)
        except (ClientError, ValueError) as e:
            if not self._is_throttle_error(e):
                raise
            logging.debug(f"{label} Rate limit Bedrock, esperando {RETRY_AFTER_THROTTLE_SECONDS}s para reintentar...")
            print(f"⏳ Rate limit Bedrock{label}, esperando {RETRY_AFTER_THROTTLE_SECONDS}s para reintentar...")
            time.sleep(RETRY_AFTER_THROTTLE_SECONDS)
            return self.model_with_tools.invoke(messages)

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

        # --- INVERSIONES: pre-fetch del perfil y enriquecimiento de contexto ---
        is_investment = (category or "").upper() == "INVERSIONES" or "inversiones" in (reason or "").lower()
        _investment_profile: Optional[dict] = None
        if is_investment:
            _investment_profile = get_profile_investor(customer_id)
            if isinstance(_investment_profile, dict):
                context_info += f"\n\n[PERFIL DE INVERSOR ACTUAL]: {json.dumps(_investment_profile, ensure_ascii=False)}"
                logging.debug(f"[claim_id={_tid}] 🏦 Perfil inversor pre-fetch: {_investment_profile}")

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
            response = self._invoke_with_retry(messages, f" [claim_id={_tid}] 1ª llamada")
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
                
                # Construir mensajes para el siguiente paso (Bedrock exige ToolMessage con tool_call_id, no mensaje human)
                current_messages = list(messages)
                current_messages.append(response)
                # Pares (tool_call_id, contenido) para cumplir formato Anthropic/Bedrock
                tool_outputs: List[tuple[str, str]] = []
                # Tracking para early return de inversiones
                _last_investment_profile: Optional[dict] = None
                _has_non_investment_tool = False

                for i, tool_call in enumerate(tool_calls):
                    try:
                        tool_call_id = getattr(tool_call, "id", None) or (tool_call.get("id") if isinstance(tool_call, dict) else None) or ""
                        tool_name = getattr(tool_call, 'name', None) or (tool_call.get('name', '') if isinstance(tool_call, dict) else '')
                        logging.debug(f"[claim_id={_tid}] 🔧 Ejecutando tool [{i+1}/{len(tool_calls)}]: {tool_name}")
                        
                        if hasattr(tool_call, "args"):
                            raw_args = tool_call.args
                        elif isinstance(tool_call, dict):
                            raw_args = tool_call.get("args", {})
                        else:
                            raw_args = {}
                        logging.debug(f"[claim_id={_tid}] 🔍 Args de tool: {raw_args}")

                        if tool_name == "execute_refinance":
                            _has_non_investment_tool = True
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
                                return AIMessage(content=message)
                            tool_outputs.append((tool_call_id, str(result)))

                        elif tool_name == "get_risk_profile":
                            logging.debug(f"[claim_id={_tid}] 🔧 Obteniendo perfil inversor customer_id={customer_id}")
                            result = get_profile_investor(customer_id)
                            _last_investment_profile = result if isinstance(result, dict) else None
                            if isinstance(result, dict):
                                tool_outputs.append((tool_call_id, json.dumps(result, ensure_ascii=False)))
                            else:
                                tool_outputs.append((tool_call_id, str(result)))

                        elif tool_name == "create_or_update_profile_investor":
                            args = dict(raw_args) if isinstance(raw_args, dict) else {}
                            args["customer_id"] = args.get("customer_id") or args.get("customerId") or customer_id
                            logging.debug(f"[claim_id={_tid}] 🔧 Creando/actualizando perfil inversor customer_id={customer_id}")
                            result = _create_profile_impl(args)
                            _last_investment_profile = result if isinstance(result, dict) else None
                            if isinstance(result, dict):
                                tool_outputs.append((tool_call_id, json.dumps(result, ensure_ascii=False)))
                            else:
                                tool_outputs.append((tool_call_id, str(result)))

                        elif tool_name == "execute_new_loan":
                            _has_non_investment_tool = True
                            args = normalize_new_loan_args(raw_args, customer_id)
                            logging.debug(f"[claim_id={_tid}] ✅ Payload new loan: amount={args.get('amount')}, quotas={args.get('quotas')}, rate={args.get('rate')}")
                            logging.debug(f"[claim_id={_tid}] 🔧 Ejecutando nuevo préstamo customer_id={customer_id}")
                            result = _execute_new_loan_impl(args)
                            logging.debug(f"[claim_id={_tid}] ✅ Resultado nuevo préstamo: {result}")
                            result_str = str(result).lower()
                            if "éxito" in result_str or "creado" in result_str:
                                logging.debug(f"[claim_id={_tid}] ✅ Nuevo préstamo exitoso, respuesta directa")
                                return AIMessage(content="Tu nuevo préstamo fue creado y el monto fue acreditado en tu cuenta.")
                            tool_outputs.append((tool_call_id, str(result)))
                        else:
                            _has_non_investment_tool = True
                            logging.debug(f"[claim_id={_tid}] ⚠️ Tool desconocida: {tool_name}")
                            tool_outputs.append((tool_call_id, f"Tool {tool_name} no reconocida"))
                    except Exception as tool_error:
                        logging.debug(f"[claim_id={_tid}] ❌ Error ejecutando tool {i+1}: {tool_error}")
                        import traceback
                        logging.debug(f"[claim_id={_tid}] " + str(traceback.format_exc()))
                        tool_outputs.append((tool_call_id, f"Error ejecutando tool: {str(tool_error)}"))
                
                # ── EARLY RETURN INVERSIONES ──
                # Si solo se ejecutaron tools de inversión, Python construye la respuesta
                # directamente sin hacer la 2ª llamada a Bedrock (evita rate limit).
                if _last_investment_profile is not None and not _has_non_investment_tool:
                    next_step = _build_investment_next_step(_last_investment_profile)
                    logging.debug(f"[claim_id={_tid}] 🏦 Inversiones: respuesta directa (sin 2ª llamada Bedrock)")
                    # Marcar sesión: si el perfil está incompleto → activa; si completo → liberar
                    rl = _last_investment_profile.get("riskLevel")
                    ml = _last_investment_profile.get("maxLossPercent")
                    hz = _last_investment_profile.get("horizon")
                    if rl and ml is not None and hz:
                        mark_investment_session_complete(customer_id)
                    else:
                        mark_investment_session_active(customer_id)
                    return AIMessage(content=next_step)

                # ── FLUJO NORMAL: 2ª llamada a Bedrock (refinanciación, préstamos, etc.) ──
                # Bedrock exige un ToolMessage por cada tool_use, con tool_call_id que coincida
                for tid, content in tool_outputs:
                    current_messages.append(ToolMessage(content=content, tool_call_id=tid))
                
                logging.debug(f"[claim_id={_tid}] INVOKE_START (2ª llamada Bedrock, post-tool)")
                print(f"⏳ Esperando {DELAY_BEFORE_SECOND_INVOKE_SECONDS}s antes de 2ª llamada a Bedrock (evitar rate limit)...")
                time.sleep(DELAY_BEFORE_SECOND_INVOKE_SECONDS)
                final_response = self._invoke_with_retry(current_messages, f" [claim_id={_tid}] 2ª llamada")
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
    