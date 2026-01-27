package com.bank.bank_ia.entities;


import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Table;
import lombok.Data;

@Entity
@Table(name = "refinance_operations")
@Data
public class RefinanceOperationEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    
    @Column(nullable = false)
    private String customerId;
    
    @ElementCollection
    @CollectionTable(name = "refinance_operation_loan_ids", joinColumns = @JoinColumn(name = "refinance_operation_id"))
    @Column(name = "loan_id")
    private List<UUID> sourceLoanIds;
    
    @Column(nullable = false)
    private BigDecimal offeredAmount;
    
    @Column(nullable = false)
    private Integer selectedQuotas;
    
    @Column(nullable = false)
    private BigDecimal appliedRate;
    
    @Column(nullable = false)
    private BigDecimal expectedCashOut;
}
