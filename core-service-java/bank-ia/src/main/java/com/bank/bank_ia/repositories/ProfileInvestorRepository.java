package com.bank.bank_ia.repositories;

import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.bank.bank_ia.entities.ProfileInvestorEntity;

public interface ProfileInvestorRepository extends JpaRepository<ProfileInvestorEntity, UUID> {
    Optional<ProfileInvestorEntity> findByCustomerId(String customerId);
}
