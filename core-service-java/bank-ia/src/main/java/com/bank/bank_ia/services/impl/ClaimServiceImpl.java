package com.bank.bank_ia.services.impl;

import java.util.Objects;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import lombok.RequiredArgsConstructor;

import com.bank.bank_ia.dto.ClaimDTO;
import com.bank.bank_ia.entities.ClaimEntity;
import com.bank.bank_ia.repositories.ClaimRepository;
import com.bank.bank_ia.services.ClaimService;


@Service
@RequiredArgsConstructor
public class ClaimServiceImpl implements ClaimService {

    private final ClaimRepository claimRepository;

    @Override
    @Transactional
    public ClaimDTO createClaim(String customerId, String message) {
        ClaimEntity claim = new ClaimEntity();
        claim.setClientId(customerId);
        claim.setOriginalMessage(message);
        claim.setStatus("RECEIVED");


        ClaimEntity savedClaim = claimRepository.save(claim);
        return new ClaimDTO(
            savedClaim.getId(), 
            savedClaim.getClientId(), 
            savedClaim.getOriginalMessage(), 
            savedClaim.getStatus(), 
            savedClaim.getCategory()
        );
    
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
