package com.bank.bank_ia.services.impl;

import java.util.List;
import java.util.Objects;

import org.springframework.stereotype.Service;

import com.bank.bank_ia.dto.LoanOfferDTO;
import com.bank.bank_ia.dto.NewLoanDTO;
import com.bank.bank_ia.entities.LoanEntity;
import com.bank.bank_ia.repositories.LoanRepository;
import com.bank.bank_ia.services.AccountService;
import com.bank.bank_ia.services.LoanOfferService;
import com.bank.bank_ia.services.newLoanService;
import lombok.RequiredArgsConstructor;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class newLoanServiceImpl implements newLoanService {
    private final LoanRepository loanRepository;
    private final LoanBuilder loanBuilder;
    private final LoanOfferService loanOfferService;
    private final AccountService accountService;

    @Override
    @Transactional
    public NewLoanDTO createNewLoan(NewLoanDTO request) {
        List<LoanOfferDTO> loanOffers = loanOfferService.getLoanOffersByCustomerId(request.customerId());
        if (loanOffers == null || loanOffers.isEmpty()) {
            throw new IllegalArgumentException("No hay ofertas de préstamo para el cliente");
        }

        boolean hasMatchingOffer = loanOffers.stream().anyMatch(offer ->
            request.amount().compareTo(offer.maxAmount()) <= 0
                && request.quotas() <= offer.maxQuotas()
                && request.rate().compareTo(offer.monthlyRate()) == 0
        );
        if (!hasMatchingOffer) {
            throw new IllegalArgumentException("No hay ofertas de préstamo que coincidan con la solicitud");
        }

        LoanEntity newLoan = Objects.requireNonNull(
            loanBuilder.buildNewLoan(request.customerId(), request.amount(), request.quotas()));
        LoanEntity savedLoan = loanRepository.save(newLoan);

        loanOfferService.deleteAllByCustomerId(request.customerId());
        accountService.addBalance(
            request.customerId(),
            request.amount(),
            "Préstamo nuevo - Ref: " + savedLoan.getLoanNumber()
        );

        return new NewLoanDTO(
            savedLoan.getCustomerId(),
            savedLoan.getTotalAmount(),
            savedLoan.getTotalQuotas(),
            request.rate()
        );
    }
}