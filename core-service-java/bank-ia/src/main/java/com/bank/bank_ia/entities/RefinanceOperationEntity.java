package com.bank.bank_ia.entities;


import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.Data;

@Entity
@Table(name = "refinance_operations")
@Data
public class RefinanceOperationEntity {
    private UUID id;
    private String customerId;
    private List<UUID> sourceLoanIds;
    private BigDecimal offeredAmount;
    private Integer selectedQuotas;
    private BigDecimal appliedRate;
    private BigDecimal expectedCashOut;
}
