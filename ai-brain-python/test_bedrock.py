#!/usr/bin/env python3
"""Script para verificar la conexión a AWS Bedrock"""

import os
import sys
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from langchain_aws import ChatBedrock

load_dotenv()

def test_bedrock_connection():
    """Prueba la conexión a AWS Bedrock"""
    print("🔍 Verificando configuración de AWS Bedrock...\n")
    
    # Verificar variables de entorno
    aws_region = os.getenv("AWS_REGION")
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    print("📋 Variables de entorno:")
    print(f"   AWS_REGION: {'✅ Configurado' if aws_region else '❌ No configurado'}")
    print(f"   AWS_ACCESS_KEY_ID: {'✅ Configurado' if aws_access_key else '❌ No configurado'}")
    print(f"   AWS_SECRET_ACCESS_KEY: {'✅ Configurado' if aws_secret_key else '❌ No configurado'}")
    print()
    
    if not all([aws_region, aws_access_key, aws_secret_key]):
        print("❌ Error: Faltan variables de entorno necesarias")
        return False
    
    # Intentar crear el cliente de Bedrock
    try:
        print("🔌 Intentando conectar a AWS Bedrock...")
        bedrock_client = boto3.client(
            service_name="bedrock-runtime",
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        print("✅ Cliente de Bedrock creado exitosamente")
    except NoCredentialsError:
        print("❌ Error: Credenciales de AWS no válidas")
        return False
    except Exception as e:
        print(f"❌ Error al crear cliente de Bedrock: {e}")
        return False
    
    # Probar con el modelo del Brain (Sonnet)
    print("\n🧠 Probando modelo Brain (Claude 3.5 Sonnet)...")
    try:
        brain_model = ChatBedrock(
            client=bedrock_client,
            model_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        )
        
        print("   Enviando mensaje de prueba...")
        response = brain_model.invoke("Responde solo con 'OK' si puedes leer esto.")
        print(f"   ✅ Respuesta recibida: {response.content[:100]}")
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        print(f"   ❌ Error de AWS: {error_code}")
        print(f"   Mensaje: {error_msg}")
        
        if error_code == 'ThrottlingException':
            print("   ⚠️  Rate limit alcanzado (pero la conexión funciona)")
        elif error_code == 'AccessDeniedException':
            print("   ⚠️  Problema de permisos - verifica IAM policies")
        elif error_code == 'ValidationException':
            print("   ⚠️  Modelo no disponible o región incorrecta")
        return False
    except Exception as e:
        print(f"   ❌ Error inesperado: {e}")
        return False
    
    # Probar con el modelo del Triage (Haiku)
    print("\n🎯 Probando modelo Triage (Claude 3 Haiku)...")
    try:
        triage_model = ChatBedrock(
            client=bedrock_client,
            model_id="us.anthropic.claude-3-haiku-20240307-v1:0",
        )
        
        print("   Enviando mensaje de prueba...")
        response = triage_model.invoke("Responde solo con 'OK' si puedes leer esto.")
        print(f"   ✅ Respuesta recibida: {response.content[:100]}")
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        print(f"   ❌ Error de AWS: {error_code}")
        print(f"   Mensaje: {error_msg}")
        return False
    except Exception as e:
        print(f"   ❌ Error inesperado: {e}")
        return False
    
    print("\n✅ ¡Todos los tests pasaron! AWS Bedrock está funcionando correctamente.")
    return True

if __name__ == "__main__":
    success = test_bedrock_connection()
    sys.exit(0 if success else 1)
