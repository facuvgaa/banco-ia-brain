package com.bank.bank_ia.services.impl;


import org.springframework.stereotype.Service;

import lombok.RequiredArgsConstructor;
import java.util.List;
import java.util.stream.Collectors;
import com.bank.bank_ia.dto.RefinanceDTO;
import com.bank.bank_ia.repositories.RefinanceRepository;
import com.bank.bank_ia.services.RefinanceService;


@Service
@RequiredArgsConstructor
public class RefinanceServiceImpl implements RefinanceService {
    private final RefinanceRepository refinanceRepository;
    
    @Override 
    public List<RefinanceDTO> getRefinancesByLoadNumber(String customerId) {
        return refinanceRepository.findByCustomerId(customerId)
        .stream()
        .map(entity -> new RefinanceDTO(
            entity.getId(), 
            entity.getLoadNumber(), 
            entity.getRemainingAmount(), 
            entity.getPaidQuotas(), 
            entity.getMonthlyQuota(), 
            entity.getCanBeRefinanced()
        ))
        .collect(Collectors.toList());
    }
}
