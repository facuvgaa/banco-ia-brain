package com.bank.bank_ia.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.UUID;

public record LoanDTO(
    UUID id,
    String loanNumber,          
    BigDecimal totalAmount,    
    BigDecimal remainingAmount, 
    BigDecimal quotaAmount,    
    Integer paidQuotas,        
    Integer totalQuotas,       
    String status,             
    LocalDateTime startDate,   
    boolean isEligibleForRefinance 
) {}
