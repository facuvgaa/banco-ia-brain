package com.bank.bank_ia.services.impl;

import java.util.Objects;
import java.util.UUID;

import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import com.bank.bank_ia.dto.ClaimDTO;
import com.bank.bank_ia.entities.ClaimEntity;
import com.bank.bank_ia.repositories.ClaimRepository;
import com.bank.bank_ia.services.ClaimService;


@Slf4j
@Service
@RequiredArgsConstructor
public class ClaimServiceImpl implements ClaimService {

    private final ClaimRepository claimRepository;
    private final KafkaTemplate<String, Object> kafkaTemplate;

    @Override
    @Transactional
    public ClaimDTO createClaim(String customerId, String message) {
        ClaimEntity claim = new ClaimEntity();
        claim.setClientId(customerId);
        claim.setOriginalMessage(message);
        claim.setStatus("RECEIVED");


        ClaimEntity savedClaim = claimRepository.save(claim);
        
        ClaimDTO claimDTO = new ClaimDTO(
            savedClaim.getId(), 
            savedClaim.getClientId(), 
            savedClaim.getOriginalMessage(), 
            savedClaim.getStatus(), 
            savedClaim.getCategory()
        );
        
        try {
            kafkaTemplate.send("claims-triage", claimDTO);
            log.info("✅ Reclamo publicado a Kafka: {}", savedClaim.getId());
        } catch (Exception e) {
            log.error("❌ Error al publicar reclamo a Kafka: {}", e.getMessage());
        }
        
        return claimDTO;
    
    }
    
    @Override
    public ClaimDTO getClaimById(UUID id) {
        Objects.requireNonNull(id, "Claim ID cannot be null");
        return claimRepository.findById(id)
        .map(entity -> new ClaimDTO(
            entity.getId(), 
            entity.getClientId(), 
            entity.getOriginalMessage(), 
            entity.getStatus(), 
            entity.getCategory()
        ))
        .orElseThrow(() -> new RuntimeException("Claim not found"));
    }
}
