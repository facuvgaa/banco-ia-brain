package com.bank.bank_ia.dto;

public record ProfileInvestorDTO(
    String customerId,
    String riskLevel, 
    Boolean hasProfile,
    Integer maxLossPercent,
    String horizon
) {}
