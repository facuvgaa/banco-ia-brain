package com.bank.bank_ia.services;


import com.bank.bank_ia.dto.ClaimDTO;
import java.util.UUID;


public interface ClaimService {
    ClaimDTO createClaim(String customerId, String message);


    ClaimDTO getClaimById(UUID id);

}