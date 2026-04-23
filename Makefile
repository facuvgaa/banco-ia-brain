.PHONY: create-kafka-topics
create-kafka-topics:
	docker exec banco-kafka kafka-topics --create --if-not-exists --topic claims-triage --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
	docker exec banco-kafka kafka-topics --create --if-not-exists --topic claims-resolutions --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1


limpiar:
	docker exec redis_memory redis-cli FLUSHALL

# facuvega-001: borra REF-* y préstamo nuevo (LOAN-timestamp), deja 2×$500k TNA 110% (6/10, refi), saldo cuenta 0. Requiere core :8080.
reset-facuvega:
	curl -sS -X POST http://localhost:8080/api/v1/bank-ia/reset/facuvega-001
