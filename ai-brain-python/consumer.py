import json
from typing import Any
from confluent_kafka import Consumer, Producer
from agents.triage_agent import TriageManager

# --- CONFIGURACIÓN DE KAFKA ---
consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'bank-ia-group',
    'auto.offset.reset': 'earliest'
})
consumer.subscribe(['claims-triage'])

producer_conf: dict[str, str] = {'bootstrap.servers': 'localhost:9092'}
response_producer = Producer(producer_conf)

# --- FUNCIÓN DE ENVÍO ---
def send_resolution_to_kafka(claim_id: str, resolution: str, status: str) -> None:
    payload: dict[str, str] = {
        'id': claim_id,
        'resolution': resolution,
        'status': status
    }
    response_producer.produce(
        'claims-resolutions',
        key=str(claim_id),
        value=json.dumps(payload).encode('utf-8')
    )
    response_producer.flush()
    print(f"📤 Evento enviado a Kafka: {status} para ID {claim_id}")

def start_consumer() -> None:
    triage: TriageManager = TriageManager()
    
    print("🚀 Monstruo escuchando en Kafka... (Ctrl+C para detener)")
    
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            
            if msg.error():
                print(f"Error: {msg.error()}")
                continue
            
            claim_data: dict[str, Any] = json.loads(msg.value().decode('utf-8'))
            claim_id: str = claim_data.get('id', '')
            user_text: str = claim_data.get('message') or claim_data.get('text', '')
            customer_id: str = claim_data.get('customerId') or claim_data.get('clientId') or 'UNKNOWN'
            
            print(f"📩 Nuevo mensaje de {customer_id}: {user_text}")

            try:
                respuesta = triage.process_chat(user_text, customer_id)
                respuesta_final: str = (
                    respuesta.response_to_user
                    if hasattr(respuesta, "response_to_user")
                    else (respuesta.content if hasattr(respuesta, "content") else str(respuesta))
                )
                print(f"🤖 IA Responde: {respuesta_final}")
                send_resolution_to_kafka(claim_id, respuesta_final, "PROCESSED")
            except Exception as e:
                print(f"❌ Error al procesar: {e}")
                send_resolution_to_kafka(
                    claim_id,
                    f"Error al procesar reclamo: {str(e)}. Por favor, contacte con soporte.",
                    "ERROR",
                )
            
    except KeyboardInterrupt:
        print("🛑 Deteniendo el Monstruo...")
    finally:
        consumer.close()

if __name__ == "__main__":
    start_consumer()