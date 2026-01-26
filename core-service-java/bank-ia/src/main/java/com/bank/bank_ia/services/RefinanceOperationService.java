package com.bank.bank_ia.services;

import java.util.List;

import com.bank.bank_ia.dto.RefinanceOperationDTO;

public interface RefinanceOperationService {
    List<RefinanceOperationDTO> getRefinanceOperationsByCustomerId(String customerId);
    void executeRefinance(RefinanceOperationDTO request);
}
