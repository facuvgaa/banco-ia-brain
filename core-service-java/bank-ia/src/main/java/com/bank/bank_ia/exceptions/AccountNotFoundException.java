package com.bank.bank_ia.exceptions;

public class AccountNotFoundException extends BusinessException {
    public AccountNotFoundException(String customerId) {
        super("ACCOUNT_NOT_FOUND", 
            String.format("Cuenta no encontrada para el cliente: %s", customerId));
    }
}
