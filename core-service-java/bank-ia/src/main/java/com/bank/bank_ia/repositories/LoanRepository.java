package com.bank.bank_ia.repositories;

import java.util.List;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.bank.bank_ia.entities.LoanEntity;

public interface LoanRepository extends JpaRepository<LoanEntity, UUID> {
    List<LoanEntity> findAllByCustomerId(String customerId);
}
