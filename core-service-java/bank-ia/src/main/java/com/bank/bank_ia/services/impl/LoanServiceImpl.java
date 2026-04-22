package com.bank.bank_ia.services.impl;

import org.springframework.stereotype.Service;
import java.util.List;
import java.util.stream.Collectors;

import com.bank.bank_ia.config.RefinanceProperties;
import com.bank.bank_ia.dto.LoanDTO;
import com.bank.bank_ia.enums.LoanStatus;
import com.bank.bank_ia.repositories.LoanRepository;
import com.bank.bank_ia.services.LoanService;

import lombok.RequiredArgsConstructor;


@Service
@RequiredArgsConstructor
public class LoanServiceImpl implements LoanService {
    private final LoanRepository loanRepository;
    private final RefinanceProperties refinanceProperties;

    @Override
    public List<LoanDTO> getLoansByCustomerId(String customerId) {
        return loanRepository.findAllByCustomerId(customerId)
        .stream()
        .map(entity -> {
            boolean eligible =
                    LoanStatus.ACTIVE.equals(entity.getStatus())
                            && entity.isEligibleForRefinance()
                            && refinanceProperties.isPaidQuotasSufficientForRefinance(
                                    entity.getPaidQuotas());
            return new LoanDTO(
            entity.getId(), 
            entity.getLoanNumber(), 
            entity.getTotalAmount(), 
            entity.getRemainingAmount(), 
            entity.getQuotaAmount(), 
            entity.getPaidQuotas(), 
            entity.getTotalQuotas(), 
            entity.getStatus() != null ? entity.getStatus().name() : null, 
            entity.getStartDate(), 
            eligible,
            entity.getNominalAnnualRate()
        );
        })
        .collect(Collectors.toList());
    }
}
