import json
import time
import re
from typing import List, Dict, Any, Union, Optional
from functools import lru_cache
from agents_config import get_brain_agent
from tools.refinance_tool import _get_refinance_context_impl, _execute_refinance_impl, get_refinance_context, execute_refinance
from tools.tool_customer_transaction import _get_customer_transactions_impl


class BrainManager:
    def __init__(self) -> None:
        self.model = get_brain_agent()
        # Solo bind execute_refinance, ya que get_refinance_context lo obtenemos antes
        self.model_with_tools = self.model.bind_tools([execute_refinance])
        # Cache simple para respuestas (TTL de 5 minutos)
        self._response_cache: Dict[str, tuple[Any, float]] = {}
        self._cache_ttl: float = 300.0  # 5 minutos

    def solve_complex_claim(self, claim_text: str, customer_id: str, reason: str, category: str) -> Any:
        context_info: str = ""
        ref_data: Union[Dict[str, Any], str, None] = None
        # Guardar mapeo de loanNumber a id para validación posterior
        loan_number_to_id_map: Dict[str, str] = {}
        eligible_loans_list: List[Dict[str, Any]] = []
        
        # Normalizamos para que "Préstamo", "prestamo" o "PRESTAMO" funcionen igual
        search_text: str = (reason + " " + category).upper()
        search_text = search_text.translate(str.maketrans("ÁÉÍÓÚ", "AEIOU"))
        
        # PERSISTENCIA: Si category es PRESTAMO o REFINANCIACION, forzamos la búsqueda de datos
        is_loan_query: bool = any(word in search_text for word in ["PRESTAMO", "REFINANCIACION", "DEUDA"])
        is_loan_category: bool = category.upper() in ["PRESTAMO", "REFINANCIACION"]
        
        # Si es categoría de préstamo O tiene palabras clave, intentamos obtener datos
        should_fetch_loan_data: bool = is_loan_query or is_loan_category

        if customer_id and customer_id != 'UNKNOWN':
            if should_fetch_loan_data:
                print(f"🚀 DEBUG: Entrando a lógica de PRESTAMOS para {customer_id} (categoría: {category})")
                try:
                    ref_data = _get_refinance_context_impl(customer_id)
                    if isinstance(ref_data, dict):
                        eligible_loans = ref_data.get("eligible_loans", [])
                        eligible_loans_list = eligible_loans if isinstance(eligible_loans, list) else []
                        new_offers = ref_data.get("new_offers", [])
                        context_info = f"\n\n[DATOS FINANCIEROS REALES]:\n"
                        context_info += f"Préstamos elegibles para refinanciar: {len(eligible_loans_list)}\n"
                        all_loan_ids = []
                        if eligible_loans_list:
                            for loan in eligible_loans_list:
                                if isinstance(loan, dict):
                                    loan_id = str(loan.get('id', 'N/A'))
                                    loan_number = loan.get('loanNumber', 'N/A')
                                    remaining = loan.get('remainingAmount', 0)
                                    paid = loan.get('paidQuotas', 0)
                                    total = loan.get('totalQuotas', 0)
                                    context_info += f"- Préstamo {loan_number} (ID: {loan_id}): ${remaining} restantes ({paid}/{total} cuotas pagadas)\n"
                                    # Guardar mapeo para validación
                                    if loan_number != 'N/A' and loan_id != 'N/A':
                                        loan_number_to_id_map[loan_number] = loan_id
                                        all_loan_ids.append(loan_id)
                            # Agregar lista completa de IDs al contexto
                            context_info += f"\n⚠️ IMPORTANTE: Debes incluir TODOS los {len(all_loan_ids)} préstamos en sourceLoanIds: {all_loan_ids}\n"
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

        # Preparar el mensaje del sistema
        system_prompt = f"""Sos un Asesor Financiero Ejecutivo de un banco argentino. Caso: {reason}.

REGLAS DE ORO:
1. NO pidas citas, NO mandes al cliente a la sucursal ni al 0800. TU TRABAJO ES HACER EL CÁLCULO ACÁ.
2. Usá los [DATOS FINANCIEROS REALES] que te paso - YA TENÉS TODOS LOS DATOS, NO necesitás pedirlos de nuevo.
3. Si hay deudas y hay ofertas, HACÉ LA CUENTA:
   - Sumá el Capital Residual de los préstamos.
   - Elegí la mejor oferta disponible.
   - Decile: "Podés cancelar tus préstamos y te sobran $[Monto] en mano".
4. Hablá de 'Capital Residual', 'Tasa Nominal Anual' y 'Sobrante'.
5. Sé ejecutivo, directo y usá un tono proactivo (Vendedor Senior).

EJECUCIÓN DE REFINANCIACIÓN:
- Si el cliente dice "procede", "acepto", "si", "dale", "confirmo", "hacelo", "adelante", "vamos", "ok", "de acuerdo", "me gustaria", "me gustaría", "refinanciar todo":
  DEBÉS usar la tool 'execute_refinance' con un diccionario JSON que contenga:
  - customerId: "{customer_id}"
  - sourceLoanIds: lista de TODOS los UUIDs de TODOS los préstamos elegibles (debe incluir TODOS los préstamos listados en [DATOS FINANCIEROS REALES], NO solo algunos)
  - offeredAmount: monto numérico de la mejor oferta
  - selectedQuotas: número entero de cuotas de la oferta elegida
  - appliedRate: tasa numérica de la oferta
  - expectedCashOut: monto numérico sobrante (offeredAmount - suma de remainingAmount de TODOS los préstamos)
  
CRÍTICO: 
1. sourceLoanIds DEBE incluir TODOS los préstamos elegibles listados, NO solo algunos.
2. sourceLoanIds DEBE ser una lista de UUIDs del campo 'id', NUNCA uses loanNumber (como "LOAN-001").
3. Si hay 5 préstamos elegibles, sourceLoanIds debe tener 5 UUIDs.
4. Usa SOLO los UUIDs que aparecen en [DATOS FINANCIEROS REALES], NO inventes UUIDs.
  
- Si el cliente NO confirma explícitamente, NO ejecutes la refinanciación, solo explicale la propuesta."""

        messages: List[tuple[str, str]] = [
            ("system", system_prompt),
            ("human", f"ID Cliente: {customer_id}\nConsulta: {claim_text}{context_info}")
        ]

        try:
            # Verificar cache primero (solo para consultas sin tool calls)
            cache_key = f"{customer_id}:{claim_text[:50]}"
            cached_response, cache_time = self._response_cache.get(cache_key, (None, 0))
            if cached_response and (time.time() - cache_time) < self._cache_ttl:
                print(f"💾 DEBUG: Usando respuesta cacheada")
                return cached_response
            
            # Pequeño delay para evitar rate limits
            time.sleep(0.5)
            
            # Usar el modelo con tools para que pueda ejecutar refinanciaciones
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
                        if hasattr(tool_call, 'args'):
                            args = tool_call.args
                        elif isinstance(tool_call, dict):
                            args = tool_call.get('args', {})
                        else:
                            args = {}
                        
                        print(f"🔍 DEBUG: Args de tool: {args}")
                        
                        # Normalizar argumentos - LangChain puede pasar argumentos en diferentes formatos
                        if isinstance(args, dict):
                            normalized_args = {}
                            if '__arg1' in args:
                                # Si solo hay un argumento, puede ser el payload completo
                                arg1 = args['__arg1']
                                if isinstance(arg1, dict):
                                    normalized_args = arg1
                                elif isinstance(arg1, str):
                                    # Si es un string, intentar parsearlo como JSON
                                    try:
                                        normalized_args = json.loads(arg1)
                                        print(f"✅ DEBUG: JSON parseado correctamente: {normalized_args}")
                                    except json.JSONDecodeError as e:
                                        print(f"⚠️  Error parseando JSON: {e}")
                                        # Si falla, usar el string como está
                                        normalized_args = {'payload': arg1}
                                else:
                                    # Si no es dict ni string, intentar construir el payload
                                    normalized_args = args.copy()
                                    normalized_args.pop('__arg1', None)
                            else:
                                normalized_args = args
                            
                            # Asegurar que customerId esté presente
                            if 'customerId' not in normalized_args and 'customer_id' not in normalized_args:
                                normalized_args['customerId'] = customer_id
                            
                            # Normalizar nombres de campos
                            if 'customer_id' in normalized_args and 'customerId' not in normalized_args:
                                normalized_args['customerId'] = normalized_args.pop('customer_id')
                            
                            # Validar y corregir sourceLoanIds - usar TODOS los préstamos disponibles si el modelo no los incluyó todos
                            if 'sourceLoanIds' in normalized_args:
                                source_loan_ids = normalized_args['sourceLoanIds']
                                print(f"🔍 DEBUG: Validando sourceLoanIds recibidos: {source_loan_ids}")
                                if isinstance(source_loan_ids, list):
                                    corrected_ids = []
                                    for loan_id in source_loan_ids:
                                        loan_id_str = str(loan_id)
                                        # Si es un loanNumber (empieza con "LOAN-"), buscar el UUID real
                                        if loan_id_str.startswith('LOAN-'):
                                            if loan_id_str in loan_number_to_id_map:
                                                corrected_ids.append(loan_number_to_id_map[loan_id_str])
                                                print(f"🔄 DEBUG: Convertido {loan_id_str} -> {loan_number_to_id_map[loan_id_str]}")
                                            else:
                                                # Intentar buscar en los datos originales si el mapeo no tiene la entrada
                                                print(f"⚠️  No se encontró UUID para {loan_id_str} en el mapeo")
                                                # Si tenemos los datos originales, buscar ahí
                                                if isinstance(ref_data, dict):
                                                    eligible_loans = ref_data.get("eligible_loans", [])
                                                    for loan in eligible_loans:
                                                        if isinstance(loan, dict) and loan.get('loanNumber') == loan_id_str:
                                                            uuid_found = str(loan.get('id', ''))
                                                            if uuid_found:
                                                                corrected_ids.append(uuid_found)
                                                                loan_number_to_id_map[loan_id_str] = uuid_found
                                                                print(f"🔄 DEBUG: Encontrado UUID desde datos: {loan_id_str} -> {uuid_found}")
                                                                break
                                                    else:
                                                        # No se encontró, mantener el original (fallará en el servidor pero al menos intentamos)
                                                        corrected_ids.append(loan_id_str)
                                                        print(f"⚠️  No se pudo convertir {loan_id_str}, se mantiene como está")
                                                else:
                                                    corrected_ids.append(loan_id_str)
                                        else:
                                            # Ya es un UUID o no está en el mapeo
                                            corrected_ids.append(loan_id_str)
                                    
                                    # VALIDACIÓN CRÍTICA: SIEMPRE usar los UUIDs reales de la base de datos, ignorar los del modelo
                                    print(f"🔍 DEBUG: Iniciando validación de UUIDs. ref_data disponible: {isinstance(ref_data, dict)}, eligible_loans_list: {len(eligible_loans_list) if eligible_loans_list else 0}")
                                    
                                    # Obtener los préstamos elegibles - primero desde ref_data, luego desde eligible_loans_list, o hacer una llamada API
                                    eligible_loans_from_data = []
                                    if isinstance(ref_data, dict):
                                        eligible_loans_from_data = ref_data.get("eligible_loans", [])
                                        print(f"🔍 DEBUG: Obtenidos {len(eligible_loans_from_data)} préstamos desde ref_data")
                                    if not eligible_loans_from_data and eligible_loans_list:
                                        eligible_loans_from_data = eligible_loans_list
                                        print(f"🔍 DEBUG: Usando {len(eligible_loans_from_data)} préstamos desde eligible_loans_list")
                                    
                                    # Si aún no tenemos datos, hacer una llamada API para obtenerlos
                                    if not eligible_loans_from_data:
                                        print(f"⚠️  No hay datos de préstamos en cache, obteniendo desde API...")
                                        try:
                                            fresh_ref_data = _get_refinance_context_impl(customer_id)
                                            if isinstance(fresh_ref_data, dict):
                                                eligible_loans_from_data = fresh_ref_data.get("eligible_loans", [])
                                                print(f"🔍 DEBUG: Obtenidos {len(eligible_loans_from_data)} préstamos desde API")
                                        except Exception as e:
                                            print(f"⚠️  Error al obtener préstamos desde API: {e}")
                                    
                                    if eligible_loans_from_data:
                                        all_available_ids = [str(loan.get('id', '')) for loan in eligible_loans_from_data if isinstance(loan, dict) and loan.get('id')]
                                        
                                        if all_available_ids:
                                            # Validar formato UUID (debe ser hexadecimal)
                                            uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
                                            valid_corrected_ids = []
                                            invalid_ids = []
                                            
                                            # Primero, verificar cuáles UUIDs del modelo son válidos y existen
                                            for loan_id in corrected_ids:
                                                loan_id_str = str(loan_id).strip()
                                                if uuid_pattern.match(loan_id_str):
                                                    # Verificar que el UUID esté en la lista de disponibles
                                                    if loan_id_str in all_available_ids:
                                                        valid_corrected_ids.append(loan_id_str)
                                                    else:
                                                        print(f"⚠️  UUID {loan_id_str} no está en los préstamos disponibles")
                                                        invalid_ids.append(loan_id_str)
                                                else:
                                                    print(f"⚠️  UUID inválido (formato incorrecto): {loan_id_str}")
                                                    invalid_ids.append(loan_id_str)
                                            
                                            # CRÍTICO: Si hay UUIDs inválidos o faltantes, REEMPLAZAR COMPLETAMENTE con los UUIDs reales
                                            if invalid_ids or len(valid_corrected_ids) != len(all_available_ids):
                                                print(f"⚠️  El modelo envió UUIDs incorrectos o incompletos.")
                                                print(f"   UUIDs enviados por modelo ({len(corrected_ids)}): {corrected_ids}")
                                                print(f"   UUIDs válidos en BD ({len(all_available_ids)}): {all_available_ids}")
                                                print(f"🔧 REEMPLAZANDO completamente con los UUIDs reales de la base de datos")
                                                corrected_ids = all_available_ids.copy()
                                            else:
                                                # Si todos son válidos, usar los que envió el modelo
                                                corrected_ids = valid_corrected_ids
                                            
                                            if invalid_ids:
                                                print(f"⚠️  Se encontraron {len(invalid_ids)} UUIDs inválidos que fueron reemplazados")
                                        else:
                                            print(f"⚠️  No se encontraron UUIDs válidos en los préstamos disponibles")
                                    else:
                                        print(f"⚠️  No se pudieron obtener préstamos elegibles para validación")
                                    
                                    normalized_args['sourceLoanIds'] = corrected_ids
                                    print(f"✅ DEBUG: sourceLoanIds validados y corregidos (total: {len(corrected_ids)}): {corrected_ids}")
                            
                            args = normalized_args
                        
                        # Ejecutar la tool correspondiente
                        if tool_name == 'execute_refinance':
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
                                    f"¡Excelente, Bernardo! La refinanciación se ha completado exitosamente. "
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