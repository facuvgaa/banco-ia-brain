package com.bank.bank_ia.services;

import java.util.List;

import com.bank.bank_ia.dto.LoanDTO;

public interface LoanService {
    List<LoanDTO> getLoansByCustomerId(String customerId);

}