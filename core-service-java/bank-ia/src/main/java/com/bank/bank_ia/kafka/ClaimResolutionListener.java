package com.bank.bank_ia.kafka;

import com.bank.bank_ia.repositories.ClaimRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.util.Objects;
import java.util.UUID;

@Component
@Slf4j
@RequiredArgsConstructor
public class ClaimResolutionListener {

    private final ClaimRepository claimRepository;
    private final ObjectMapper objectMapper;

    @KafkaListener(topics = "claims-resolutions", groupId = "bank-ia-core-group")
    public void listenResolution(String message) {
        try {
            log.info("📥 Mensaje crudo de Kafka: {}", message);
            
            JsonNode json;
            try {
                json = objectMapper.readTree(message);
            } catch (com.fasterxml.jackson.core.JsonProcessingException e) {
                log.error("❌ Error parseando JSON: {}", message, e);
                return;
            }
            
            if (!json.has("id") || !json.has("status")) {
                log.error("❌ JSON inválido: faltan campos requeridos (id, status). JSON recibido: {}", message);
                return;
            }
            
            String idString = json.get("id").asText();
            final UUID claimId;
            try {
                claimId = Objects.requireNonNull(UUID.fromString(idString), "El ID del reclamo no puede ser null");
            } catch (IllegalArgumentException e) {
                log.error("❌ ID inválido (no es un UUID válido): {}", idString);
                return;
            }
            
            String status = json.get("status").asText();
            if (status == null || status.trim().isEmpty()) {
                log.error("❌ Status no puede estar vacío para el reclamo: {}", claimId);
                return;
            }
            
            String resolution = json.has("resolution") && !json.get("resolution").isNull() 
                ? json.get("resolution").asText() 
                : null;
            
            String category = json.has("category") && !json.get("category").isNull() 
                ? json.get("category").asText() 
                : null;

            claimRepository.findById(claimId).ifPresentOrElse(claim -> {
                claim.setStatus(status);
                
                if (resolution != null) {
                    claim.setResolution(resolution);
                }
                
                if (category != null) {
                    claim.setCategory(category);
                }
                
                claimRepository.save(claim);
                log.info("✅ Reclamo {} actualizado exitosamente a {}", claimId, status);
            }, () -> log.warn("⚠️ No se encontró el reclamo con ID: {}", claimId));

        } catch (Exception e) {
            log.error("❌ Error inesperado procesando la resolución de la IA", e);
        }
    }
}
