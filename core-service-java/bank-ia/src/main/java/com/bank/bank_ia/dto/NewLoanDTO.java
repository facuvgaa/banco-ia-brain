package com.bank.bank_ia.dto;

import java.math.BigDecimal;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

@NotNull(message = "El customerId es requerido")
@NotBlank(message = "El customerId no puede estar vacío")
@Size(min = 1, max = 255, message = "El customerId debe tener entre 1 y 255 caracteres")
public record NewLoanDTO(
    String customerId,
    BigDecimal amount,
    Integer quotas,
    BigDecimal rate
) {}