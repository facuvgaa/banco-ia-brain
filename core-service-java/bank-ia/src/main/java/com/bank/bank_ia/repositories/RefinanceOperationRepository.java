package com.bank.bank_ia.repositories;

import java.util.UUID;
import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

import com.bank.bank_ia.entities.RefinanceOperationEntity;

public interface RefinanceOperationRepository extends JpaRepository<RefinanceOperationEntity, UUID> {
    List<RefinanceOperationEntity> findByCustomerId(String customerId);
}
