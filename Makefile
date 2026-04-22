.PHONY: create-kafka-topics
create-kafka-topics:
	docker exec banco-kafka kafka-topics --create --if-not-exists --topic claims-triage --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
	docker exec banco-kafka kafka-topics --create --if-not-exists --topic claims-resolutions --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1


limpiar:
	docker exec redis_memory redis-cli FLUSHALL

# Restaura préstamos demo y borra REF-* para facuvega-001 (tras probar refinancio). Requiere core en :8080.
reset-facuvega:
	curl -sS -X POST http://localhost:8080/api/v1/bank-ia/reset/facuvega-001
