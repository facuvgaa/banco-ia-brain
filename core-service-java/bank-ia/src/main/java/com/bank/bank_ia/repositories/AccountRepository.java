package com.bank.bank_ia.repositories;

import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import com.bank.bank_ia.entities.AccountEntity;

public interface AccountRepository extends JpaRepository<AccountEntity, UUID> {
    @Query("SELECT a.active FROM AccountEntity a WHERE a.customerId = :customerId")
    boolean isAccountActive(@Param("customerId") String customerId);
    
    Optional<AccountEntity> findByCustomerId(String customerId);
}
