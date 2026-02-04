package com.bank.bank_ia.dto;

import java.math.BigDecimal;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

public record NewLoanRequestDTO(
    @NotNull(message = "El monto es requerido")
    @Positive(message = "El monto debe ser mayor a cero")
    BigDecimal amount,

    @NotNull(message = "El número de cuotas es requerido")
    @Positive(message = "El número de cuotas debe ser mayor a cero")
    Integer quotas,

    @NotNull(message = "La tasa es requerida")
    @Positive(message = "La tasa debe ser mayor a cero")
    BigDecimal rate
) {}
