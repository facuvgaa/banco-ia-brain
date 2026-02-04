package com.bank.bank_ia.services.impl;

import java.util.List;
import java.util.stream.Collectors;

import org.springframework.stereotype.Service;

import com.bank.bank_ia.dto.LoanOfferDTO;
import com.bank.bank_ia.repositories.LoanOfferRepository;
import com.bank.bank_ia.services.LoanOfferService;

import lombok.RequiredArgsConstructor;


@Service
@RequiredArgsConstructor
public class LoanOfferServiceImpl implements LoanOfferService {
    private final LoanOfferRepository loanOfferRepository;

    @Override
    public List<LoanOfferDTO> getLoanOffersByCustomerId(String customerId) {
        return loanOfferRepository.findAllByCustomerId(customerId)
        .stream()
        .map(entity -> new LoanOfferDTO(
            entity.getMaxAmount(),
            entity.getMaxQuotas(),
            entity.getMonthlyRate(),
            entity.getMinDTI()
        ))
        .collect(Collectors.toList());
    }

    @Override
    public void deleteAllByCustomerId(String customerId) {
       var offers = loanOfferRepository.findAllByCustomerId(customerId);
       if (!offers.isEmpty()) {
        loanOfferRepository.deleteAll(offers);
       }
    }
}
