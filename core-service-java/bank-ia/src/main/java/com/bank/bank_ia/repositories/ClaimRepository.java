package com.bank.bank_ia.repositories;

import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.bank.bank_ia.entities.ClaimEntity;

public interface ClaimRepository extends JpaRepository<ClaimEntity, UUID> {
    
}
