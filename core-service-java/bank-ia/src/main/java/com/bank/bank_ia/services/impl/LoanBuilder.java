package com.bank.bank_ia.services.impl;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.UUID;

import org.springframework.stereotype.Component;

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
        LoanEntity loan = new LoanEntity();
        loan.setId(UUID.randomUUID());
        loan.setCustomerId(request.customerId());
        loan.setLoanNumber(generateLoanNumber());
        loan.setTotalAmount(request.offeredAmount());
        loan.setRemainingAmount(request.offeredAmount());
        loan.setQuotaAmount(calculateQuotaAmount(request.offeredAmount(), request.selectedQuotas()));
        loan.setTotalQuotas(request.selectedQuotas());
        loan.setPaidQuotas(0);
        loan.setStatus(LoanStatus.ACTIVE);
        loan.setStartDate(LocalDateTime.now());
        loan.setEligibleForRefinance(false);
        
        return loan;
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
