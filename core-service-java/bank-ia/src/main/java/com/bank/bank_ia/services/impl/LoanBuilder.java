package com.bank.bank_ia.services.impl;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.UUID;

import org.springframework.stereotype.Component;

import com.bank.bank_ia.config.LoanConstants;
import com.bank.bank_ia.config.RefinanceProperties;
import com.bank.bank_ia.dto.RefinanceOperationDTO;
import com.bank.bank_ia.entities.LoanEntity;
import com.bank.bank_ia.enums.LoanStatus;

import lombok.RequiredArgsConstructor;

/**
 * Builder para crear entidades LoanEntity de forma consistente.
 * Encapsula la lógica de construcción de préstamos.
 */
@Component
@RequiredArgsConstructor
public class LoanBuilder {
    
    private final RefinanceProperties refinanceProperties;
    
    /**
     * Crea un nuevo préstamo de refinanciación basado en la operación.
     */
    public LoanEntity buildRefinanceLoan(RefinanceOperationDTO request) {
        return buildRefinanceLoan(request, request.offeredAmount());
    }

    /**
     * Crea un nuevo préstamo de refinanciación usando el monto resuelto (ej. desde la oferta en BD).
     */
    public LoanEntity buildRefinanceLoan(RefinanceOperationDTO request, BigDecimal offeredAmount) {
        LoanEntity loan = new LoanEntity();
        loan.setId(UUID.randomUUID());
        loan.setCustomerId(request.customerId());
        loan.setLoanNumber(generateLoanNumber());
        loan.setTotalAmount(offeredAmount);
        loan.setRemainingAmount(offeredAmount);
        loan.setQuotaAmount(calculateQuotaAmount(offeredAmount, request.selectedQuotas()));
        loan.setTotalQuotas(request.selectedQuotas());
        loan.setPaidQuotas(0);
        loan.setStatus(LoanStatus.ACTIVE);
        loan.setStartDate(LocalDateTime.now());
        loan.setEligibleForRefinance(false);

        return loan;
    }

    /**
     * Crea un nuevo préstamo (no refinanciación) para la misma tabla de préstamos (loads).
     * Se usa cuando el cliente toma una oferta de nuevo préstamo.
     */
    public LoanEntity buildNewLoan(String customerId, BigDecimal amount, Integer quotas) {
        LoanEntity loan = new LoanEntity();
        loan.setId(UUID.randomUUID());
        loan.setCustomerId(customerId);
        loan.setLoanNumber(generateNewLoanNumber());
        loan.setTotalAmount(amount);
        loan.setRemainingAmount(amount);
        loan.setQuotaAmount(calculateQuotaAmount(amount, quotas));
        loan.setTotalQuotas(quotas);
        loan.setPaidQuotas(0);
        loan.setStatus(LoanStatus.ACTIVE);
        loan.setStartDate(LocalDateTime.now());
        loan.setEligibleForRefinance(false);
        return loan;
    }

    private String generateNewLoanNumber() {
        return LoanConstants.STANDARD_LOAN_PREFIX + System.currentTimeMillis();
    }
    
    private String generateLoanNumber() {
        return refinanceProperties.getLoanPrefix() + System.currentTimeMillis();
    }
    
    private BigDecimal calculateQuotaAmount(BigDecimal totalAmount, Integer quotas) {
        return totalAmount.divide(
            new BigDecimal(quotas), 
            refinanceProperties.getQuotaDecimalScale(), 
            refinanceProperties.getQuotaRoundingMode()
        );
    }
}
