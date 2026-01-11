package com.bank.bank_ia.dto;

import java.math.BigDecimal;
import java.util.UUID;
import java.time.LocalDateTime;

public record TransactionDTO(
    UUID id,
    BigDecimal amount,
    String currency,
    String status,
    LocalDateTime transactionDate,
    String description
) {}