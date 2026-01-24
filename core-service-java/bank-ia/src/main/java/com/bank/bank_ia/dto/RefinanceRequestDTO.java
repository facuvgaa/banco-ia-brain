package com.bank.bank_ia.dto;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

public record RefinanceRequestDTO(
    String customerId,
    List<UUID> loanIdsToCancel,
    BigDecimal newTotalAmount,
    Integer quotas
) {}
