package com.bank.bank_ia.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.UUID;

/**
 * DTO de respuesta para operaciones de refinanciación exitosas.
 */
public record RefinanceResponseDTO(
    String message,
    String customerId,
    UUID newLoanId,
    String newLoanNumber,
    BigDecimal totalDebtCanceled,
    BigDecimal cashOut,
    /** TNA % aplicada al nuevo préstamo. */
    BigDecimal appliedNominalAnnualRate,
    LocalDateTime timestamp
) {
    public static RefinanceResponseDTO of(
            String customerId,
            UUID newLoanId,
            String newLoanNumber,
            BigDecimal totalDebtCanceled,
            BigDecimal cashOut,
            BigDecimal appliedNominalAnnualRate) {
        return new RefinanceResponseDTO(
            "Refinanciación exitosa",
            customerId,
            newLoanId,
            newLoanNumber,
            totalDebtCanceled,
            cashOut,
            appliedNominalAnnualRate,
            LocalDateTime.now()
        );
    }
}
