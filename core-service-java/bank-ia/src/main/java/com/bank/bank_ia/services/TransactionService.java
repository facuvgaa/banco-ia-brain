package com.bank.bank_ia.services;

import java.util.List;

import com.bank.bank_ia.dto.TransactionDTO;

public interface TransactionService {
    List<TransactionDTO> getCustomerTransactions(String customerId);
}
