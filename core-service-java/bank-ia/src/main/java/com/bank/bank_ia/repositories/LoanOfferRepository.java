package com.bank.bank_ia.repositories;
import java.util.List;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.bank.bank_ia.entities.LoanOfferEntity;

public interface LoanOfferRepository extends JpaRepository<LoanOfferEntity, UUID> {
    List<LoanOfferEntity> findAllByCustomerId(String customerId);
}
