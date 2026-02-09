package com.bank.bank_ia.services;

import java.util.Optional;

import com.bank.bank_ia.dto.ProfileInvestorDTO;

public interface ProfileInvestorService {

    Optional<ProfileInvestorDTO> getProfileInvestorByCustomerId(String customerId);

    ProfileInvestorDTO createOrUpdateProfile(String customerId, ProfileInvestorDTO dto);

}
