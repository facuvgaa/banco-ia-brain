package com.bank.bank_ia.dto;

import java.math.BigDecimal;
import java.util.UUID;

public record AccountDTO(
    UUID id,
    String customerId,
    String accountNumber, 
    BigDecimal balance,    
    String accountType,   
    boolean isActive    
) {}
