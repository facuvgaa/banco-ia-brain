package com.bank.bank_ia.dto;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;


public record RefinanceOperationDTO(
    String customerId,
    List<UUID> sourceLoanIds,    
    BigDecimal offeredAmount,    
    Integer selectedQuotas,      
    BigDecimal appliedRate,     
    BigDecimal expectedCashOut
) {}