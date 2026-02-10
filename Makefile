.PHONY: create-kafka-topics
create-kafka-topics:
	docker exec banco-kafka kafka-topics --create --if-not-exists --topic claims-triage --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
	docker exec banco-kafka kafka-topics --create --if-not-exists --topic claims-resolutions --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
