package com.bank.bank_ia.services;

import com.bank.bank_ia.dto.NewLoanDTO;

public interface newLoanService {
    NewLoanDTO createNewLoan(NewLoanDTO request);
}
