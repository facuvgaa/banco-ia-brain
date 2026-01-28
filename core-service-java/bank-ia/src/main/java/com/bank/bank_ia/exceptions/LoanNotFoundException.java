package com.bank.bank_ia.exceptions;

import java.util.List;
import java.util.UUID;

public class LoanNotFoundException extends BusinessException {
    public LoanNotFoundException(String message) {
        super("LOAN_NOT_FOUND", message);
    }
    
    public LoanNotFoundException(List<UUID> loanIds) {
        super("LOAN_NOT_FOUND", 
            String.format("No se encontraron préstamos válidos para refinanciar con los IDs proporcionados: %s", loanIds));
    }
}
