import json
from confluent_kafka import Consumer
from triage_agent import TriageManager
from brain_agent import BrainManager

consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'bank-ia-group',
    'auto.offset.reset': 'earliest'
})
consumer.subscribe(['claims-triage'])

# Inicializamos los Agentes
triage_manager = TriageManager()
brain_manager = BrainManager()

print("🚀 Sistema de Inteligencia Bancaria Activo...")

try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None: continue
        
        claim_data = json.loads(msg.value().decode('utf-8'))
        message = claim_data['message']
        
        print(f"\n📩 Recibido: '{message}'")

        triage_result = triage_manager.process_claim(message)
        
        if triage_result.decision == "ESCALATE":
            print(f"⚠️  Triage: ESCALANDO (Razón: {triage_result.reason})")
            
            response = brain_manager.solve_complex_claim(message, triage_result.reason)
            print(f"🧠 Brain dice: {response.content}")
            
        else:
            print(f"✅ Triage: RESOLVIENDO directamente.")
            print(f"🤖 Respuesta: {triage_result.response_to_user}")

except KeyboardInterrupt:
    print("Deteniendo...")
finally:
    consumer.close()