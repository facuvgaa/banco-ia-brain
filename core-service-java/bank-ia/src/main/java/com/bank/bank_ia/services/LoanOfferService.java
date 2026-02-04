package com.bank.bank_ia.services;

import java.util.List;

import com.bank.bank_ia.dto.LoanOfferDTO;

public interface LoanOfferService {
    List<LoanOfferDTO> getLoanOffersByCustomerId(String customerId);
    
    void deleteAllByCustomerId(String customerId);
}
