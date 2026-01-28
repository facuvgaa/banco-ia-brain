package com.bank.bank_ia.services.impl;


import java.util.List;
import java.util.stream.Collectors;

import org.springframework.stereotype.Service;

import com.bank.bank_ia.dto.TransactionDTO;
import com.bank.bank_ia.repositories.TransactionRepository;
import com.bank.bank_ia.services.TransactionService;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class TransactionServiceImpl implements TransactionService{
    private final TransactionRepository transactionRepository;

    @Override
    public List<TransactionDTO> getCustomerTransactions(String customerId) {
        return transactionRepository.findByCustomerId(customerId)
        .stream()
        .map(entity -> new TransactionDTO(
            entity.getId(), 
            entity.getAmount(), 
            entity.getCurrency(),
            entity.getStatus() != null ? entity.getStatus().name() : null,
            entity.getCoelsaId(),
            entity.getTransactionDate(),
            entity.getDescription()
        ))
        .collect(Collectors.toList());
    }
}
