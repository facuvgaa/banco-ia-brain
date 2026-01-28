package com.bank.bank_ia.services.impl;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.bank.bank_ia.config.LoanConstants;
import com.bank.bank_ia.entities.LoanEntity;
import com.bank.bank_ia.entities.LoanOfferEntity;
import com.bank.bank_ia.enums.LoanStatus;
import com.bank.bank_ia.repositories.LoanOfferRepository;
import com.bank.bank_ia.repositories.LoanRepository;
import com.bank.bank_ia.services.RefinanceResetService;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Service
@RequiredArgsConstructor
@Slf4j
public class RefinanceResetServiceImpl implements RefinanceResetService {
    
    private final LoanRepository loanRepository;
    private final LoanOfferRepository loanOfferRepository;
    
    // Configuración de préstamos de prueba - debería venir de un archivo de configuración
    private static final Map<String, LoanConfig> LOAN_CONFIGS = Map.of(
        "LOAN-001", new LoanConfig(new BigDecimal("500000.00"), 0),
        "LOAN-002", new LoanConfig(new BigDecimal("120000.00"), 6),
        "LOAN-003", new LoanConfig(new BigDecimal("160000.00"), 6),
        "LOAN-004", new LoanConfig(new BigDecimal("140000.00"), 3),
        "LOAN-005", new LoanConfig(new BigDecimal("175000.00"), 3)
    );
    
    @Override
    @Transactional
    public ResetResult resetCustomerData(String customerId) {
        log.info("Reseteando datos del cliente: {}", customerId);
        
        int deletedRefinanceLoans = deleteRefinanceLoans(customerId);
        int restoredLoans = restoreOriginalLoans(customerId);
        int createdOffers = createDefaultOffers(customerId);
        
        return new ResetResult(restoredLoans, deletedRefinanceLoans, createdOffers);
    }
    
    private int deleteRefinanceLoans(String customerId) {
        List<LoanEntity> refinanceLoans = loanRepository.findAllByCustomerId(customerId)
            .stream()
            .filter(loan -> loan.getLoanNumber() != null && loan.getLoanNumber().startsWith(LoanConstants.REFINANCE_LOAN_PREFIX))
            .toList();
        
        if (!refinanceLoans.isEmpty()) {
            loanRepository.deleteAll(refinanceLoans);
            log.info("Eliminados {} préstamos de refinanciación", refinanceLoans.size());
        }
        
        return refinanceLoans.size();
    }
    
    private int restoreOriginalLoans(String customerId) {
        List<LoanEntity> closedLoans = loanRepository.findAllByCustomerId(customerId)
            .stream()
            .filter(loan -> LoanStatus.CLOSED_BY_REFINANCE.equals(loan.getStatus()))
            .toList();
        
        for (LoanEntity loan : closedLoans) {
            LoanConfig config = LOAN_CONFIGS.get(loan.getLoanNumber());
            if (config != null) {
                loan.setStatus(LoanStatus.ACTIVE);
                loan.setRemainingAmount(config.remainingAmount());
                loan.setPaidQuotas(config.paidQuotas());
                loan.setEligibleForRefinance(true);
            }
        }
        
        if (!closedLoans.isEmpty()) {
            loanRepository.saveAll(closedLoans);
            log.info("Restaurados {} préstamos a estado ACTIVE", closedLoans.size());
        }
        
        return closedLoans.size();
    }
    
    private int createDefaultOffers(String customerId) {
        List<LoanOfferEntity> existingOffers = loanOfferRepository.findAllByCustomerId(customerId);
        if (!existingOffers.isEmpty()) {
            return 0;
        }
        
        List<LoanOfferEntity> offers = List.of(
            createOffer(customerId, new BigDecimal("1500000.00"), 60, new BigDecimal("75.0"), new BigDecimal("0.3")),
            createOffer(customerId, new BigDecimal("2000000.00"), 36, new BigDecimal("80.5"), new BigDecimal("0.35")),
            createOffer(customerId, new BigDecimal("1200000.00"), 24, new BigDecimal("65.5"), new BigDecimal("0.25")),
            createOffer(customerId, new BigDecimal("2500000.00"), 48, new BigDecimal("89.9"), new BigDecimal("0.4"))
        );
        
        if (!offers.isEmpty()) {
           loanOfferRepository.saveAll(offers);
            log.info("Creadas {} nuevas ofertas de préstamo", offers.size());
        
           return offers.size();
        }
        
        return 0;
    }
    
    private LoanOfferEntity createOffer(String customerId, BigDecimal maxAmount, 
                                       Integer maxQuotas, BigDecimal monthlyRate, BigDecimal minDTI) {
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
