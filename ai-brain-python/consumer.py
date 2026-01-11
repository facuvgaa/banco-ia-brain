import json
from confluent_kafka import Consumer, Producer
from triage_agent import TriageManager
from brain_agent import BrainManager

# --- CONFIGURACIÓN ---
consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'bank-ia-group',
    'auto.offset.reset': 'earliest'
})
consumer.subscribe(['claims-triage'])

producer_conf = {'bootstrap.servers': 'localhost:9092'}
response_producer = Producer(producer_conf)

triage_manager = TriageManager()
brain_manager = BrainManager()

# --- FUNCIÓN DE ENVÍO ---
def send_resolution_to_kafka(claim_id, resolution, status):
    payload = {
        'id': claim_id, # Usamos 'id' para que coincida con el UUID de Java
        'resolution': resolution,
        'status': status
    }
    response_producer.produce(
        'claims-resolutions', # Asegúrate que el tópico coincida con Java
        key=str(claim_id),
        value=json.dumps(payload).encode('utf-8')
    )
    response_producer.flush()
    print(f"📤 Evento enviado a Kafka: {status} para ID {claim_id}")

print("🚀 Sistema de Inteligencia Bancaria Activo...")

try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None: continue
        if msg.error():
            print(f"Error: {msg.error()}")
            continue
        
        claim_data = json.loads(msg.value().decode('utf-8'))
        claim_id = claim_data['id']
        message = claim_data['message']
        
        print(f"\n📩 Recibido reclamo {claim_id}: '{message}'")

        triage_result = triage_manager.process_claim(message)
        
        if triage_result.decision == "ESCALATE":
            print(f"⚠️  Triage: ESCALANDO (Razón: {triage_result.reason})")
            
            brain_response = brain_manager.solve_complex_claim(message, triage_result.reason)
            # Enviamos la respuesta del Brain
            send_resolution_to_kafka(claim_id, brain_response.content, "ESCALATED")
            
        else:
            print(f"✅ Triage: RESOLVIENDO directamente.")
            # Enviamos la respuesta del Triage
            send_resolution_to_kafka(claim_id, triage_result.response_to_user, "PROCESSED")

except KeyboardInterrupt:
    print("Deteniendo...")
finally:
    consumer.close()