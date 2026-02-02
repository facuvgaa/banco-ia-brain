package com.bank.bank_ia.services.impl;

import com.bank.bank_ia.services.AccountService;
import org.springframework.stereotype.Service;
import lombok.RequiredArgsConstructor;
import org.springframework.transaction.annotation.Transactional;
import java.math.BigDecimal;
import java.util.UUID;
import java.time.LocalDateTime;
import com.bank.bank_ia.repositories.AccountRepository;
import com.bank.bank_ia.repositories.TransactionRepository;
import com.bank.bank_ia.entities.AccountEntity;
import com.bank.bank_ia.entities.TransactionEntity;
import com.bank.bank_ia.dto.AccountDTO;
import com.bank.bank_ia.enums.TransactionStatus;

@Service
@RequiredArgsConstructor
public class AccountServiceImpl implements AccountService {
    private final AccountRepository accountRepository;
    private final TransactionRepository transactionRepository;

    @Override
    public AccountDTO getAccountByCustomerId(String customerId) {
        AccountEntity account = accountRepository.findByCustomerId(customerId)
                .orElseThrow(() -> new com.bank.bank_ia.exceptions.AccountNotFoundException(customerId));
        
        return new AccountDTO(
            account.getId(),
            account.getCustomerId(),
            account.getAccountNumber(),
            account.getBalance(),
            account.getAccountType() != null ? account.getAccountType().name() : null,
            accountRepository.isAccountActive(customerId)
        );
    }

    @Override
    @Transactional
    public void addBalance(String customerId, BigDecimal amount, String description) {
        // 1. Buscamos la cuenta del cliente
        AccountEntity account = accountRepository.findByCustomerId(customerId)
                .orElseThrow(() -> new com.bank.bank_ia.exceptions.AccountNotFoundException(customerId));

        // 2. Actualizamos el saldo
        account.setBalance(account.getBalance().add(amount));
        accountRepository.save(account);

        // 3. Creamos el movimiento contable (La auditoría)
        TransactionEntity transaction = new TransactionEntity();
        transaction.setCustomerId(customerId);
        transaction.setAmount(amount);
        transaction.setCurrency("ARS");
        transaction.setDescription(description);
        transaction.setStatus(TransactionStatus.SUCCESS);
        transaction.setTransactionDate(LocalDateTime.now());
        // Generamos un ID de seguimiento único
        transaction.setCoelsaId("REF-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());

        transactionRepository.save(transaction);
    }

    @Override
    public boolean isAccountActive(String customerId) {
        return accountRepository.findByCustomerId(customerId)
                .map(AccountEntity::isActive)
                .orElse(false);
    }
}