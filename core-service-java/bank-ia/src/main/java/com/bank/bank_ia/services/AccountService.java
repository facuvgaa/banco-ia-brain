package com.bank.bank_ia.services;

import java.math.BigDecimal;

import com.bank.bank_ia.dto.AccountDTO;

public interface AccountService {
    AccountDTO getAccountByCustomerId(String customerId);
    void addBalance(String customerId, BigDecimal amount, String description);
    boolean isAccountActive(String customerId);
}
