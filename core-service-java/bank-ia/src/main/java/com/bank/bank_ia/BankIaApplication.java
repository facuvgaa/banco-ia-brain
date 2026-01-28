package com.bank.bank_ia;

import com.bank.bank_ia.entities.AccountEntity;
import com.bank.bank_ia.entities.LoanEntity;
import com.bank.bank_ia.entities.TransactionEntity;
import com.bank.bank_ia.enums.AccountType;
import com.bank.bank_ia.enums.LoanStatus;
import com.bank.bank_ia.enums.TransactionStatus;
import com.bank.bank_ia.repositories.AccountRepository;
import com.bank.bank_ia.repositories.LoanRepository;
import com.bank.bank_ia.repositories.TransactionRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Objects;
import java.util.UUID;

@SpringBootApplication
public class BankIaApplication {

    public static void main(String[] args) {
        SpringApplication.run(BankIaApplication.class, args);
    }

    @Bean
    CommandLineRunner seedTransactions(TransactionRepository repository) {
        return args -> {
            // Verificamos si ya hay datos para no duplicar en cada reinicio
            if (repository.count() == 0) {
                // Registro 1: Una transferencia que falló (ideal para que el Brain la encuentre)
                repository.save(Objects.requireNonNull(TransactionEntity.builder()
                        .customerId("BERNARDO-001")
                        .amount(new BigDecimal("55000.00"))
                        .currency("ARS")
                        .status(TransactionStatus.FAILED)
                        .coelsaId("COELSA-001")
                        .transactionDate(LocalDateTime.now().minusHours(2))
                        .description("Transferencia enviada a CBU 00000234...")
                        .build()));

                // Registro 2: Un gasto común completado
                repository.save(Objects.requireNonNull(TransactionEntity.builder()
                        .customerId("BERNARDO-001")
                        .amount(new BigDecimal("4500.00"))
                        .currency("ARS")
                        .status(TransactionStatus.COMPLETED)
                        .coelsaId("COELSA-002")
                        .transactionDate(LocalDateTime.now().minusDays(1))
                        .description("Compra en Supermercado")
                        .build()));

                // Registro 3: Ejemplo basado en comprobante de $517.759,00
                repository.save(Objects.requireNonNull(TransactionEntity.builder()
                        .customerId("BERNARDO-001")
                        .amount(new BigDecimal("517759.00"))
                        .currency("ARS")
                        .status(TransactionStatus.FAILED) // Simulamos que falló pero tiene código
                        .transactionDate(LocalDateTime.now().minusHours(5))
                        .description("Transferencia a Holding Srl")
                        .coelsaId("LMORZP891OOMGF22EGJ568") // <-- El código del comprobante
                        .build()));

                System.out.println("✅ Datos de prueba de transacciones insertados en Postgres.");
            }
        };
    }

    @Bean
    CommandLineRunner seedLoans(LoanRepository loanRepository) {
        return args -> {
            // Verificamos si ya hay datos para no duplicar en cada reinicio
            if (loanRepository.count() == 0) {
                // 1. Préstamo habilitado (ACTIVE) - nuevo, sin cuotas pagadas
                LoanEntity activeLoan = new LoanEntity();
                activeLoan.setId(UUID.randomUUID());
                activeLoan.setCustomerId("BERNARDO-001");
                activeLoan.setLoanNumber("LOAN-001");
                activeLoan.setTotalAmount(new BigDecimal("500000.00"));
                activeLoan.setRemainingAmount(new BigDecimal("500000.00"));
                activeLoan.setQuotaAmount(new BigDecimal("50000.00"));
                activeLoan.setPaidQuotas(0);
                activeLoan.setTotalQuotas(10);
                activeLoan.setStatus(LoanStatus.ACTIVE);
                activeLoan.setStartDate(LocalDateTime.now().minusMonths(1));
                activeLoan.setEligibleForRefinance(true);
                loanRepository.save(activeLoan);

                // 2. Préstamo con 6 cuotas pagadas
                LoanEntity loan6Quotas1 = new LoanEntity();
                loan6Quotas1.setId(UUID.randomUUID());
                loan6Quotas1.setCustomerId("BERNARDO-001");
                loan6Quotas1.setLoanNumber("LOAN-002");
                loan6Quotas1.setTotalAmount(new BigDecimal("300000.00"));
                loan6Quotas1.setRemainingAmount(new BigDecimal("120000.00")); // 4 cuotas restantes de 10
                loan6Quotas1.setQuotaAmount(new BigDecimal("30000.00"));
                loan6Quotas1.setPaidQuotas(6);
                loan6Quotas1.setTotalQuotas(10);
                loan6Quotas1.setStatus("ACTIVE");
                loan6Quotas1.setStartDate(LocalDateTime.now().minusMonths(7));
                loan6Quotas1.setEligibleForRefinance(true);
                loanRepository.save(loan6Quotas1);

                // 3. Otro préstamo con 6 cuotas pagadas
                LoanEntity loan6Quotas2 = new LoanEntity();
                loan6Quotas2.setId(UUID.randomUUID());
                loan6Quotas2.setCustomerId("BERNARDO-001");
                loan6Quotas2.setLoanNumber("LOAN-003");
                loan6Quotas2.setTotalAmount(new BigDecimal("400000.00"));
                loan6Quotas2.setRemainingAmount(new BigDecimal("160000.00")); // 4 cuotas restantes de 10
                loan6Quotas2.setQuotaAmount(new BigDecimal("40000.00"));
                loan6Quotas2.setPaidQuotas(6);
                loan6Quotas2.setTotalQuotas(10);
                loan6Quotas2.setStatus("ACTIVE");
                loan6Quotas2.setStartDate(LocalDateTime.now().minusMonths(8));
                loan6Quotas2.setEligibleForRefinance(true);
                loanRepository.save(loan6Quotas2);

                // 4. Préstamo con 3 cuotas pagadas
                LoanEntity loan3Quotas1 = new LoanEntity();
                loan3Quotas1.setId(UUID.randomUUID());
                loan3Quotas1.setCustomerId("BERNARDO-001");
                loan3Quotas1.setLoanNumber("LOAN-004");
                loan3Quotas1.setTotalAmount(new BigDecimal("200000.00"));
                loan3Quotas1.setRemainingAmount(new BigDecimal("140000.00")); // 7 cuotas restantes de 10
                loan3Quotas1.setQuotaAmount(new BigDecimal("20000.00"));
                loan3Quotas1.setPaidQuotas(3);
                loan3Quotas1.setTotalQuotas(10);
                loan3Quotas1.setStatus("ACTIVE");
                loan3Quotas1.setStartDate(LocalDateTime.now().minusMonths(4));
                loan3Quotas1.setEligibleForRefinance(true);
                loanRepository.save(loan3Quotas1);

                // 5. Otro préstamo con 3 cuotas pagadas
                LoanEntity loan3Quotas2 = new LoanEntity();
                loan3Quotas2.setId(UUID.randomUUID());
                loan3Quotas2.setCustomerId("BERNARDO-001");
                loan3Quotas2.setLoanNumber("LOAN-005");
                loan3Quotas2.setTotalAmount(new BigDecimal("250000.00"));
                loan3Quotas2.setRemainingAmount(new BigDecimal("175000.00")); // 7 cuotas restantes de 10
                loan3Quotas2.setQuotaAmount(new BigDecimal("25000.00"));
                loan3Quotas2.setPaidQuotas(3);
                loan3Quotas2.setTotalQuotas(10);
                loan3Quotas2.setStatus("ACTIVE");
                loan3Quotas2.setStartDate(LocalDateTime.now().minusMonths(5));
                loan3Quotas2.setEligibleForRefinance(true);
                loanRepository.save(loan3Quotas2);

                System.out.println("✅ Datos de prueba de préstamos insertados en Postgres.");
                System.out.println("   - 1 préstamo habilitado (0 cuotas pagadas)");
                System.out.println("   - 2 préstamos con 6 cuotas pagadas");
                System.out.println("   - 2 préstamos con 3 cuotas pagadas");
            }
        };
    }

    @Bean
    CommandLineRunner seedAccounts(AccountRepository accountRepository) {
        return args -> {
            // Verificamos si ya hay una cuenta para BERNARDO-001
            if (accountRepository.findByCustomerId("BERNARDO-001").isEmpty()) {
                AccountEntity account = new AccountEntity();
                account.setCustomerId("BERNARDO-001");
                account.setAccountNumber("ACC-" + System.currentTimeMillis());
                account.setBalance(new BigDecimal("100000.00")); // Saldo inicial
                account.setAccountType(AccountType.CHECKING);
                account.setActive(true);
                accountRepository.save(account);
                
                System.out.println("✅ Cuenta de prueba creada para BERNARDO-001.");
            }
        };
    }
}