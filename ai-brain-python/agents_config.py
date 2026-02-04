import os
import boto3
from botocore.config import Config
from langchain_aws import ChatBedrock
from dotenv import load_dotenv

load_dotenv()

# --- RATE LIMIT (429) EN BEDROCK ---
# Causas: (1) Cuota baja (RPM/tokens por minuto). (2) Reintentos: con max_attempts>1,
# ante 429 botocore reintenta = más requests y más throttling. (3) Mensaje 1 y 2 seguidos.
# Mitigación: max_attempts=1 (no reintentar en 429; fallar rápido sin enviar 2ª request)
# y delay largo antes del 2º mensaje para no superar RPM.
BEDROCK_RETRY_CONFIG = Config(retries={"max_attempts": 1, "mode": "standard"})


TRIAGE_PROMPT = """
Eres el Triage de un banco. Tu función es analizar el mensaje del usuario.
- Si es una duda general o saludo: RESPONDE (RESOLVE).
- Si el usuario quiere sacar un préstamo, pagar deudas, refinanciar o ver movimientos: ESCALA (ESCALATE).
Categorías: TRANSFERENCIA, SALDO, PRESTAMO, REFINANCIACION.
"""

BRAIN_LOAN_PROMPT = """
Sos el Especialista en Préstamos. Tu objetivo es ayudar a refinanciar deudas.
1. SIEMPRE usá 'get_refinance_context' para ver qué debe el cliente y qué ofertas hay.
2. Compará la tasa (interestRate) vieja vs la nueva.
3. Calculá el sobrante: Monto Oferta - Deuda Actual.
4. Si le conviene (tasa más baja), ofrecelo resaltando el ahorro y el dinero extra.
5. NO ejecutes 'execute_refinance' sin confirmación explícita ("Acepto", "Si", "Dale").
"""

# --- CONFIGURACIÓN DE CLIENTE Y AGENTES ---
# Un solo cliente Bedrock para todo el proceso (evita clientes duplicados y posibles dobles llamadas).
_bedrock_client = None

def get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client(
            service_name="bedrock-runtime",
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            config=BEDROCK_RETRY_CONFIG,
        )
    return _bedrock_client

def get_triangle_agent():
    return ChatBedrock(
        client=get_bedrock_client(),
        model_id="us.anthropic.claude-3-haiku-20240307-v1:0",
    )

def get_brain_agent():
    return ChatBedrock(
        client=get_bedrock_client(),
        model_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
    )
