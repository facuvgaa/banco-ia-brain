package com.bank.bank_ia.dto;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;

public record RefinanceOperationDTO(
    @NotBlank(message = "El customerId es requerido")
    String customerId,
    
    @NotEmpty(message = "Debe especificar al menos un préstamo para refinanciar")
    @Size(min = 1, message = "Debe especificar al menos un préstamo")
    List<UUID> sourceLoanIds,    
    
    @NotNull(message = "El monto ofrecido es requerido")
    @Positive(message = "El monto ofrecido debe ser mayor a cero")
    BigDecimal offeredAmount,    
    
    @NotNull(message = "El número de cuotas es requerido")
    @Positive(message = "El número de cuotas debe ser mayor a cero")
    Integer selectedQuotas,      
    
    @NotNull(message = "La tasa aplicada es requerida")
    @Positive(message = "La tasa aplicada debe ser mayor a cero")
    BigDecimal appliedRate,     
    
    @NotNull(message = "El cash out esperado es requerido")
    BigDecimal expectedCashOut
) {}