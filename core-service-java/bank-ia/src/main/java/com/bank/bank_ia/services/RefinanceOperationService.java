package com.bank.bank_ia.services;

import java.util.List;

import com.bank.bank_ia.dto.RefinanceOperationDTO;
import com.bank.bank_ia.dto.RefinanceResponseDTO;

public interface RefinanceOperationService {
    List<RefinanceOperationDTO> getRefinanceOperationsByCustomerId(String customerId);
    RefinanceResponseDTO executeRefinance(RefinanceOperationDTO request);
}
