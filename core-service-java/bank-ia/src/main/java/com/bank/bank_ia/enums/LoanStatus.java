package com.bank.bank_ia.enums;

/**
 * Estados posibles de un préstamo.
 */
public enum LoanStatus {
    ACTIVE("Activo"),
    CLOSED_BY_REFINANCE("Cerrado por refinanciación"),
    PAID_OFF("Pagado completamente"),
    DEFAULTED("En mora"),
    CANCELLED("Cancelado");
    
    private final String description;
    
    LoanStatus(String description) {
        this.description = description;
    }
    
    public String getDescription() {
        return description;
    }
    
    /**
     * Verifica si el préstamo está elegible para refinanciación.
     */
    public boolean isEligibleForRefinance() {
        return this == ACTIVE;
    }
}
