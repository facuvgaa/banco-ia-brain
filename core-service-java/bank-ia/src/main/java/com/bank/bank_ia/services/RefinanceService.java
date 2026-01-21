package com.bank.bank_ia.services;

import java.util.List;

import com.bank.bank_ia.dto.RefinanceDTO;

public interface RefinanceService {
    List<RefinanceDTO> getRefinancesByLoadNumber(String customerId);
    
}
