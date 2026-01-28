package com.bank.bank_ia.enums;

/**
 * Tipos de cuenta bancaria disponibles.
 */
public enum AccountType {
    CHECKING("Cuenta Corriente"),
    SAVINGS("Caja de Ahorro"),
    BUSINESS("Cuenta Empresarial");
    
    private final String description;
    
    AccountType(String description) {
        this.description = description;
    }
    
    public String getDescription() {
        return description;
    }
}
