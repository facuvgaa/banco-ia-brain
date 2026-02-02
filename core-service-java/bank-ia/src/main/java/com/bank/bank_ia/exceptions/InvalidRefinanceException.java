package com.bank.bank_ia.exceptions;

import java.math.BigDecimal;
import java.util.UUID;

public class InvalidRefinanceException extends BusinessException {
    public InvalidRefinanceException(String message) {
        super("INVALID_REFINANCE", message);
    }
    
    public static InvalidRefinanceException insufficientAmount(BigDecimal offeredAmount, BigDecimal totalDebt) {
        return new InvalidRefinanceException(
            String.format("El monto ofrecido (%.2f) no cubre la deuda actual (%.2f)", 
                offeredAmount, totalDebt)
        );
    }
    
    public static InvalidRefinanceException loanNotBelongsToCustomer(UUID loanId, String customerId) {
        return new InvalidRefinanceException(
            String.format("El préstamo %s no pertenece al cliente %s", loanId, customerId)
        );
    }
    
    public static InvalidRefinanceException emptyLoanList() {
        return new InvalidRefinanceException("No se especificaron préstamos para refinanciar");
    }

    public static InvalidRefinanceException noMatchingOffer() {
        return new InvalidRefinanceException(
            "No se encontró una oferta del cliente que coincida con las cuotas y tasa indicadas"
        );
    }

    public static InvalidRefinanceException offeredAmountOutOfRange(
            BigDecimal offeredAmount, BigDecimal totalDebt, BigDecimal maxAmount) {
        return new InvalidRefinanceException(
            String.format(
                "El monto solicitado (%.2f) debe ser mayor o igual a la deuda a cancelar (%.2f) y menor o igual al máximo de la oferta (%.2f)",
                offeredAmount, totalDebt, maxAmount
            )
        );
    }
}
