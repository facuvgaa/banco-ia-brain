package com.bank.bank_ia.repositories;

import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.bank.bank_ia.entities.AccountEntity;
import java.math.BigDecimal;

public interface AccountRepository extends JpaRepository<AccountEntity, UUID> {
    void addBalance(String customerId, BigDecimal amount, String description);

    boolean isAccountActive(String customerId);
    
    Optional<AccountEntity> findByCustomerId(String customerId);
}
