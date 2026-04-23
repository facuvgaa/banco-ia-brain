package com.bank.bank_ia.services.impl;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.bank.bank_ia.config.LoanConstants;
import com.bank.bank_ia.config.RefinanceProperties;
import com.bank.bank_ia.entities.LoanEntity;
import com.bank.bank_ia.entities.LoanOfferEntity;
import com.bank.bank_ia.enums.LoanStatus;
import com.bank.bank_ia.repositories.AccountRepository;
import com.bank.bank_ia.repositories.LoanOfferRepository;
import com.bank.bank_ia.repositories.LoanRepository;
import com.bank.bank_ia.services.RefinanceResetService;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Service
@RequiredArgsConstructor
@Slf4j
public class RefinanceResetServiceImpl implements RefinanceResetService {

    public static final String FACU_DEMO_CUSTOMER = "facuvega-001";

    private final LoanRepository loanRepository;
    private final LoanOfferRepository loanOfferRepository;
    private final AccountRepository accountRepository;
    private final RefinanceProperties refinanceProperties;

    // Restaurar préstamos BERNARDO u otros (solo remaining + paid; TNA/ total vienen de la fila)
    private static final Map<String, LoanConfig> LOAN_CONFIGS = Map.ofEntries(
            Map.entry("LOAN-001", new LoanConfig(new BigDecimal("500000.00"), 0)),
            Map.entry("LOAN-002", new LoanConfig(new BigDecimal("120000.00"), 6)),
            Map.entry("LOAN-003", new LoanConfig(new BigDecimal("160000.00"), 6)),
            Map.entry("LOAN-004", new LoanConfig(new BigDecimal("140000.00"), 3)),
            Map.entry("LOAN-005", new LoanConfig(new BigDecimal("175000.00"), 3)));

    @Override
    @Transactional
    public void ensureFacuDemoLoansIfApplicable(String customerId) {
        syncFacuvegaDemoLoansIfApplicable(customerId);
    }

    @Override
    @Transactional
    public ResetResult resetCustomerData(String customerId) {
        log.info("Reseteando datos del cliente: {}", customerId);

        int deletedRefinance = deleteRefinanceLoans(customerId);
        int deletedNew = deleteApiGeneratedNewLoans(customerId);
        int restored = restoreOriginalLoans(customerId);
        syncFacuvegaDemoLoansIfApplicable(customerId);
        clearAccountBalance(customerId);
        int created = createDefaultOffers(customerId);

        return new ResetResult(restored, deletedRefinance, deletedNew, created);
    }

    private int deleteRefinanceLoans(String customerId) {
        List<LoanEntity> refin =
                loanRepository.findAllByCustomerId(customerId).stream()
                        .filter(
                                loan ->
                                        loan.getLoanNumber() != null
                                                && loan.getLoanNumber()
                                                        .startsWith(LoanConstants.REFINANCE_LOAN_PREFIX))
                        .toList();
        if (!refin.isEmpty()) {
            loanRepository.deleteAll(refin);
            log.info("Eliminados {} préstamos REF-*", refin.size());
        }
        return refin.size();
    }

    /**
     * Préstamos creados por {@code create_new_loan}: número "LOAN-" + timestamp (solo dígitos, largo).
     */
    private int deleteApiGeneratedNewLoans(String customerId) {
        String pfx = LoanConstants.STANDARD_LOAN_PREFIX;
        List<LoanEntity> apiLoans =
                loanRepository.findAllByCustomerId(customerId).stream()
                        .filter(
                                loan -> {
                                    String n = loan.getLoanNumber();
                                    if (n == null || !n.startsWith(pfx)) {
                                        return false;
                                    }
                                    String rest = n.substring(pfx.length());
                                    return rest.length() >= 10
                                            && rest.chars().allMatch(Character::isDigit);
                                })
                        .toList();
        if (!apiLoans.isEmpty()) {
            loanRepository.deleteAll(apiLoans);
            log.info("Eliminados {} préstamos de nuevo crédito (LOAN-timestamp)", apiLoans.size());
        }
        return apiLoans.size();
    }

    private int restoreOriginalLoans(String customerId) {
        List<LoanEntity> closed =
                loanRepository.findAllByCustomerId(customerId).stream()
                        .filter(loan -> LoanStatus.CLOSED_BY_REFINANCE.equals(loan.getStatus()))
                        .toList();

        for (LoanEntity loan : closed) {
            if (isFacuDemoNumber(loan.getLoanNumber())) {
                applyFacuDemoState(loan);
            } else {
                LoanConfig config = LOAN_CONFIGS.get(loan.getLoanNumber());
                if (config != null) {
                    loan.setStatus(LoanStatus.ACTIVE);
                    loan.setRemainingAmount(config.remainingAmount());
                    loan.setPaidQuotas(config.paidQuotas());
                    loan.setEligibleForRefinance(
                            refinanceProperties.isPaidQuotasSufficientForRefinance(
                                    config.paidQuotas()));
                }
            }
        }
        if (!closed.isEmpty()) {
            loanRepository.saveAll(closed);
            log.info("Restaurados {} préstamos desde CLOSED_BY_REFINANCE", closed.size());
        }
        return closed.size();
    }

    /**
     * Asegura estado demo para FACU-001/002 (aunque ya estuvieran ACTIVE o vengan de restore);
     * crea las filas si faltan.
     */
    private void syncFacuvegaDemoLoansIfApplicable(String customerId) {
        if (!FACU_DEMO_CUSTOMER.equals(customerId)) {
            return;
        }
        var all = loanRepository.findAllByCustomerId(customerId);
        for (String num : List.of("FACU-001", "FACU-002")) {
            var existing =
                    all.stream().filter(l -> num.equals(l.getLoanNumber())).findFirst();
            if (existing.isEmpty()) {
                LoanEntity created = new LoanEntity();
                created.setId(UUID.randomUUID());
                created.setCustomerId(customerId);
                created.setLoanNumber(num);
                applyFacuDemoState(created);
                loanRepository.save(created);
                log.info("Creado préstamo demo {}", num);
            } else {
                applyFacuDemoState(existing.get());
                loanRepository.save(existing.get());
            }
        }
    }

    private static boolean isFacuDemoNumber(String loanNumber) {
        return "FACU-001".equals(loanNumber) || "FACU-002".equals(loanNumber);
    }

    private void applyFacuDemoState(LoanEntity loan) {
        loan.setStatus(LoanStatus.ACTIVE);
        loan.setTotalAmount(new BigDecimal("500000.00"));
        loan.setRemainingAmount(new BigDecimal("200000.00"));
        loan.setQuotaAmount(new BigDecimal("50000.00"));
        loan.setPaidQuotas(6);
        loan.setTotalQuotas(10);
        loan.setStartDate(LocalDateTime.now().minusMonths(6));
        loan.setNominalAnnualRate(new BigDecimal("110.0"));
        loan.setEligibleForRefinance(
                refinanceProperties.isPaidQuotasSufficientForRefinance(6));
    }

    private void clearAccountBalance(String customerId) {
        if (!FACU_DEMO_CUSTOMER.equals(customerId)) {
            return;
        }
        accountRepository
                .findByCustomerId(customerId)
                .ifPresent(
                        acc -> {
                            acc.setBalance(BigDecimal.ZERO);
                            accountRepository.save(acc);
                            log.info("Saldo de cuenta a 0 para {}", customerId);
                        });
    }

    private int createDefaultOffers(String customerId) {
        List<LoanOfferEntity> existing = loanOfferRepository.findAllByCustomerId(customerId);
        if (!existing.isEmpty()) {
            return 0;
        }
        List<LoanOfferEntity> offers =
                List.of(
                        createOffer(
                                customerId,
                                new BigDecimal("1500000.00"),
                                60,
                                new BigDecimal("75.0"),
                                new BigDecimal("0.3")),
                        createOffer(
                                customerId,
                                new BigDecimal("2000000.00"),
                                36,
                                new BigDecimal("80.5"),
                                new BigDecimal("0.35")),
                        createOffer(
                                customerId,
                                new BigDecimal("1200000.00"),
                                24,
                                new BigDecimal("65.5"),
                                new BigDecimal("0.25")),
                        createOffer(
                                customerId,
                                new BigDecimal("2500000.00"),
                                48,
                                new BigDecimal("89.9"),
                                new BigDecimal("0.4")));
        loanOfferRepository.saveAll(offers);
        log.info("Creadas {} ofertas de préstamo", offers.size());
        return offers.size();
    }

    private LoanOfferEntity createOffer(
            String customerId, BigDecimal maxAmount, int maxQuotas, BigDecimal monthlyRate, BigDecimal minDTI) {
        LoanOfferEntity offer = new LoanOfferEntity();
        offer.setId(UUID.randomUUID());
        offer.setCustomerId(customerId);
        offer.setMaxAmount(maxAmount);
        offer.setMaxQuotas(maxQuotas);
        offer.setMonthlyRate(monthlyRate);
        offer.setMinDTI(minDTI);
        return offer;
    }

    private record LoanConfig(BigDecimal remainingAmount, Integer paidQuotas) {}
}
