package com.bank.bank_ia.dto;

import java.math.BigDecimal;

public record LoanOfferDTO (
    BigDecimal maxAmount,    
    Integer maxQuotas,       
    BigDecimal monthlyRate,  
    BigDecimal minDTI
){}
