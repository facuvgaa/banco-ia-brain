import os
import boto3
from langchain_aws import ChatBedrock
from dotenv import load_dotenv

load_dotenv()


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

def get_bedrock_client():
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )

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
