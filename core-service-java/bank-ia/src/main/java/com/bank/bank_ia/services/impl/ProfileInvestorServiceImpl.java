package com.bank.bank_ia.services.impl;

import java.util.Optional;

import org.springframework.stereotype.Service;

import com.bank.bank_ia.dto.ProfileInvestorDTO;
import com.bank.bank_ia.repositories.ProfileInvestorRepository;
import com.bank.bank_ia.services.ProfileInvestorService;
import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class ProfileInvestorServiceImpl implements ProfileInvestorService {
    private final ProfileInvestorRepository profileInvestorRepository;

    @Override
    public Optional<ProfileInvestorDTO> getProfileInvestorByCustomerId(String customerId) {
        return profileInvestorRepository.findByCustomerId(customerId)
        .map(entity -> new ProfileInvestorDTO(
            entity.getCustomerId(),
            entity.getRiskLevel(),
            entity.getHasProfile(),
            entity.getMaxLossPercent(),
            entity.getHorizon()
        )); 
    }
}
