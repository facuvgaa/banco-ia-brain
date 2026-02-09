package com.bank.bank_ia.services.impl;

import java.util.Optional;

import org.springframework.stereotype.Service;

import com.bank.bank_ia.dto.ProfileInvestorDTO;
import com.bank.bank_ia.entities.ProfileInvestorEntity;
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
    @Override
    public ProfileInvestorDTO createOrUpdateProfile(String customerId, ProfileInvestorDTO dto) {
        ProfileInvestorEntity entity = profileInvestorRepository.findByCustomerId(customerId)
            .orElse(new ProfileInvestorEntity());
        entity.setCustomerId(customerId);
        // Solo actualizar campos que vienen con valor (update parcial sin pisar datos existentes)
        if (dto.riskLevel() != null) entity.setRiskLevel(dto.riskLevel());
        if (dto.hasProfile() != null) entity.setHasProfile(dto.hasProfile());
        else if (entity.getHasProfile() == null) entity.setHasProfile(false);
        if (dto.maxLossPercent() != null) entity.setMaxLossPercent(dto.maxLossPercent());
        if (dto.horizon() != null) entity.setHorizon(dto.horizon());
        ProfileInvestorEntity saved = profileInvestorRepository.save(entity);
        return new ProfileInvestorDTO(
            saved.getCustomerId(),
            saved.getRiskLevel(),
            saved.getHasProfile(),
            saved.getMaxLossPercent(),
            saved.getHorizon()
        );
    }
}
