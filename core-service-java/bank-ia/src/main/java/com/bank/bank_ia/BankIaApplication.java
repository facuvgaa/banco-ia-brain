package com.bank.bank_ia;

import com.bank.bank_ia.entities.AccountEntity;
import com.bank.bank_ia.entities.LoanEntity;
import com.bank.bank_ia.entities.LoanOfferEntity;
import com.bank.bank_ia.entities.TransactionEntity;
import com.bank.bank_ia.enums.AccountType;
import com.bank.bank_ia.enums.LoanStatus;
import com.bank.bank_ia.enums.TransactionStatus;
import com.bank.bank_ia.repositories.AccountRepository;
import com.bank.bank_ia.repositories.LoanOfferRepository;
import com.bank.bank_ia.repositories.LoanRepository;
import com.bank.bank_ia.repositories.TransactionRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.core.annotation.Order;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

@SpringBootApplication
public class BankIaApplication {

    public static void main(String[] args) {
        SpringApplication.run(BankIaApplication.class, args);
    }

    /**
     * Datos de prueba (orden garantizado con @Order):
     * - BERNARDO-001: refinanciación (tiene préstamos, cuenta, transacciones; ofertas se crean con POST /reset/{customerId}).
     * - CARLOS-NO-REF: nuevo préstamo (préstamos con menos de 6 cuotas pagadas = no refinanciable, cuenta, 1 oferta disponible).
     */
    @Bean
    @Order(1)
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
    @Order(2)
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
                activeLoan.setNominalAnnualRate(new BigDecimal("80.0"));
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
                loan6Quotas1.setStatus(LoanStatus.ACTIVE);
                loan6Quotas1.setStartDate(LocalDateTime.now().minusMonths(7));
                loan6Quotas1.setEligibleForRefinance(true);
                loan6Quotas1.setNominalAnnualRate(new BigDecimal("78.0"));
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
                loan6Quotas2.setStatus(LoanStatus.ACTIVE);
                loan6Quotas2.setStartDate(LocalDateTime.now().minusMonths(8));
                loan6Quotas2.setEligibleForRefinance(true);
                loan6Quotas2.setNominalAnnualRate(new BigDecimal("78.0"));
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
                loan3Quotas1.setStatus(LoanStatus.ACTIVE);
                loan3Quotas1.setStartDate(LocalDateTime.now().minusMonths(4));
                loan3Quotas1.setEligibleForRefinance(true);
                loan3Quotas1.setNominalAnnualRate(new BigDecimal("76.0"));
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
                loan3Quotas2.setStatus(LoanStatus.ACTIVE);
                loan3Quotas2.setStartDate(LocalDateTime.now().minusMonths(5));
                loan3Quotas2.setEligibleForRefinance(true);
                loan3Quotas2.setNominalAnnualRate(new BigDecimal("75.0"));
                loanRepository.save(loan3Quotas2);

                // Usuario que NO puede refinanciar (< 6 cuotas pagadas) pero tiene oferta para nuevo préstamo
                String noRefinanceCustomerId = "CARLOS-NO-REF";
                LoanEntity loanNoRef1 = new LoanEntity();
                loanNoRef1.setId(UUID.randomUUID());
                loanNoRef1.setCustomerId(noRefinanceCustomerId);
                loanNoRef1.setLoanNumber("LOAN-NOREF-001");
                loanNoRef1.setTotalAmount(new BigDecimal("150000.00"));
                loanNoRef1.setRemainingAmount(new BigDecimal("120000.00"));
                loanNoRef1.setQuotaAmount(new BigDecimal("15000.00"));
                loanNoRef1.setPaidQuotas(2);
                loanNoRef1.setTotalQuotas(10);
                loanNoRef1.setStatus(LoanStatus.ACTIVE);
                loanNoRef1.setStartDate(LocalDateTime.now().minusMonths(3));
                loanNoRef1.setEligibleForRefinance(false);
                loanNoRef1.setNominalAnnualRate(new BigDecimal("90.0"));
                loanRepository.save(loanNoRef1);

                LoanEntity loanNoRef2 = new LoanEntity();
                loanNoRef2.setId(UUID.randomUUID());
                loanNoRef2.setCustomerId(noRefinanceCustomerId);
                loanNoRef2.setLoanNumber("LOAN-NOREF-002");
                loanNoRef2.setTotalAmount(new BigDecimal("200000.00"));
                loanNoRef2.setRemainingAmount(new BigDecimal("160000.00"));
                loanNoRef2.setQuotaAmount(new BigDecimal("20000.00"));
                loanNoRef2.setPaidQuotas(2);
                loanNoRef2.setTotalQuotas(10);
                loanNoRef2.setStatus(LoanStatus.ACTIVE);
                loanNoRef2.setStartDate(LocalDateTime.now().minusMonths(2));
                loanNoRef2.setEligibleForRefinance(false);
                loanNoRef2.setNominalAnnualRate(new BigDecimal("88.0"));
                loanRepository.save(loanNoRef2);

                System.out.println("✅ Datos de prueba de préstamos insertados en Postgres.");
                System.out.println("   - 1 préstamo habilitado (0 cuotas pagadas)");
                System.out.println("   - 2 préstamos con 6 cuotas pagadas");
                System.out.println("   - 2 préstamos con 3 cuotas pagadas");
                System.out.println("   - Usuario CARLOS-NO-REF: 2 préstamos con 2 cuotas pagadas (no refinanciable)");
            }
        };
    }

    @Bean
    @Order(3)
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
            // Usuario que no puede refinanciar pero tiene oferta para nuevo préstamo
            if (accountRepository.findByCustomerId("CARLOS-NO-REF").isEmpty()) {
                AccountEntity account = new AccountEntity();
                account.setCustomerId("CARLOS-NO-REF");
                account.setAccountNumber("ACC-NOREF-" + System.currentTimeMillis());
                account.setBalance(new BigDecimal("50000.00"));
                account.setAccountType(AccountType.CHECKING);
                account.setActive(true);
                accountRepository.save(account);
                System.out.println("✅ Cuenta de prueba creada para CARLOS-NO-REF (no refinanciable, con oferta disponible).");
            }
            // Chat / demo: refinancio acredita cash-out vía AccountService.addBalance
            if (accountRepository.findByCustomerId("facuvega-001").isEmpty()) {
                AccountEntity account = new AccountEntity();
                account.setCustomerId("facuvega-001");
                account.setAccountNumber("ACC-FACU-" + System.currentTimeMillis());
                account.setBalance(new BigDecimal("0.00"));
                account.setAccountType(AccountType.CHECKING);
                account.setActive(true);
                accountRepository.save(account);
                System.out.println("✅ Cuenta de prueba creada para facuvega-001.");
            }
        };
    }

    @Bean
    @Order(4)
    CommandLineRunner seedLoanOffersNoRefinanceUser(LoanOfferRepository loanOfferRepository) {
        return args -> {
            String customerId = "CARLOS-NO-REF";
            if (loanOfferRepository.findAllByCustomerId(customerId).isEmpty()) {
                LoanOfferEntity offer = new LoanOfferEntity();
                offer.setId(UUID.randomUUID());
                offer.setCustomerId(customerId);
                offer.setMaxAmount(new BigDecimal("300000.00"));
                offer.setMaxQuotas(24);
                offer.setMonthlyRate(new BigDecimal("2.5"));
                offer.setMinDTI(new BigDecimal("0.3"));
                loanOfferRepository.save(offer);
                System.out.println("✅ Oferta de préstamo creada para CARLOS-NO-REF (nuevo préstamo disponible).");
            }
        };
    }

    /**
     * Mismo universo de prueba que BERNARDO-001, para el customerId del chat (facuvega-001):
     * préstamo refinanciable + ofertas, si aún no hay filas.
     */
    @Bean
    @Order(5)
    CommandLineRunner seedFacuvegaChatUser(LoanRepository loanRepository, LoanOfferRepository loanOfferRepository) {
        return args -> {
            String customerId = "facuvega-001";
            if (loanRepository.findAllByCustomerId(customerId).isEmpty()) {
                // Dos préstamos de $500.000, TNA 80%, 6/10 cuotas pagas → refinanciables (mismo perfil c/u)
                for (String num : List.of("FACU-001", "FACU-002")) {
                    LoanEntity t = new LoanEntity();
                    t.setId(UUID.randomUUID());
                    t.setCustomerId(customerId);
                    t.setLoanNumber(num);
                    t.setTotalAmount(new BigDecimal("500000.00"));
                    t.setRemainingAmount(new BigDecimal("200000.00"));
                    t.setQuotaAmount(new BigDecimal("50000.00"));
                    t.setPaidQuotas(6);
                    t.setTotalQuotas(10);
                    t.setStatus(LoanStatus.ACTIVE);
                    t.setStartDate(LocalDateTime.now().minusMonths(6));
                    t.setEligibleForRefinance(true);
                    t.setNominalAnnualRate(new BigDecimal("80.0"));
                    loanRepository.save(t);
                }
                System.out.println("✅ Préstamos de demo insertados para facuvega-001 (2×$500k, TNA 80%, 6/10, refinanciables).");
            }
            if (loanOfferRepository.findAllByCustomerId(customerId).isEmpty()) {
                List<LoanOfferEntity> offers = List.of(
                        buildOffer(customerId, new BigDecimal("1500000.00"), 60, new BigDecimal("75.0"), new BigDecimal("0.3")),
                        buildOffer(customerId, new BigDecimal("2000000.00"), 36, new BigDecimal("80.5"), new BigDecimal("0.35")),
                        buildOffer(customerId, new BigDecimal("1200000.00"), 24, new BigDecimal("65.5"), new BigDecimal("0.25")),
                        buildOffer(customerId, new BigDecimal("2500000.00"), 48, new BigDecimal("89.9"), new BigDecimal("0.4"))
                );
                loanOfferRepository.saveAll(offers);
                System.out.println("✅ Ofertas de demo insertadas para facuvega-001.");
            }
        };
    }

    private static LoanOfferEntity buildOffer(
            String customerId, BigDecimal maxAmount, int maxQuotas, BigDecimal monthlyRate, BigDecimal minDti) {
        LoanOfferEntity offer = new LoanOfferEntity();
        offer.setId(UUID.randomUUID());
        offer.setCustomerId(customerId);
        offer.setMaxAmount(maxAmount);
        offer.setMaxQuotas(maxQuotas);
        offer.setMonthlyRate(monthlyRate);
        offer.setMinDTI(minDti);
        return offer;
    }
}