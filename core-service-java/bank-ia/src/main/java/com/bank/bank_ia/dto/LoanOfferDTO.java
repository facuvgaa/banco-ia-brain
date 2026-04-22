package com.bank.bank_ia.dto;

import java.math.BigDecimal;
import java.util.UUID;

/**
 * Ofertas de préstamo. {@code monthlyRate} conserva el nombre de columna en BD; {@code annualNominalRate} es TNA % (mismo valor de negocio en esta demo).
 */
public record LoanOfferDTO(
    UUID id,
    BigDecimal maxAmount,
    Integer maxQuotas,
    BigDecimal monthlyRate,
    BigDecimal annualNominalRate,
    BigDecimal minDTI
) {
}
