package com.bank.bank_ia.dto;

import java.util.UUID;
import java.math.BigDecimal;

public record RefinanceDTO(
    UUID id,
    String loadNumber,
    BigDecimal remainingAmount,
    Integer paidQuotas,
    BigDecimal monthlyQuota,
    BigDecimal interestRate,
    Boolean canBeRefinanced
) {}
