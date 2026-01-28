package com.bank.bank_ia.entities;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.UUID;

import com.bank.bank_ia.enums.LoanStatus;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Data;

@Entity
@Table(name = "loads")
@Data
public class LoanEntity {
    @Id
    private UUID id;
    
    @Column(nullable = false)
    private String customerId;
    
    @Column(nullable = false)
    private String loanNumber;
    
    @Column(nullable = false)
    private BigDecimal totalAmount;
    
    @Column(nullable = false)
    private BigDecimal remainingAmount;
    
    @Column(nullable = false)
    private BigDecimal quotaAmount;
    
    @Column(nullable = false)
    private Integer paidQuotas;
    
    @Column(nullable = false)
    private Integer totalQuotas;
    
    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private LoanStatus status;
    
    @Column(nullable = false)
    private LocalDateTime startDate;
    
    @Column(nullable = false)
    private boolean isEligibleForRefinance;
}
