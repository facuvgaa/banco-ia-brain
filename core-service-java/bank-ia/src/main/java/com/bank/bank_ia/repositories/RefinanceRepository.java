package com.bank.bank_ia.repositories;

import java.util.List;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.bank.bank_ia.entities.RefinanceEntity;

public interface RefinanceRepository extends JpaRepository<RefinanceEntity, UUID> {
    List<RefinanceEntity> findByCustomerId(String customerId);
}
