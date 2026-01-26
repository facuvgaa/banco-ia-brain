package com.bank.bank_ia.entities;

import java.math.BigDecimal;
import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Data;

@Entity
@Table(name = "accounts")
@Data
public class AccountEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    @Column(nullable = false)
    private String customerId;
    @Column(nullable = false)
    private String accountNumber;
    @Column(nullable = false)
    private BigDecimal balance;
    @Column(nullable = false)
    private String accountType;
    
    @Column(nullable = false)
    private boolean active = true;
}
