package com.bank.bank_ia.enums;

/**
 * Estados posibles de una transacción.
 */
public enum TransactionStatus {
    SUCCESS("Exitosa"),
    FAILED("Fallida"),
    PENDING("Pendiente"),
    COMPLETED("Completada"),
    CANCELLED("Cancelada");
    
    private final String description;
    
    TransactionStatus(String description) {
        this.description = description;
    }
    
    public String getDescription() {
        return description;
    }
}
