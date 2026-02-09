package com.bank.bank_ia.controllers;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.bank.bank_ia.dto.ClaimDTO;
import com.bank.bank_ia.dto.TransactionDTO;
import com.bank.bank_ia.services.ClaimService;
import com.bank.bank_ia.services.LoanOfferService;
import com.bank.bank_ia.services.LoanService;
import com.bank.bank_ia.services.ProfileInvestorService;
import com.bank.bank_ia.services.RefinanceOperationService;
import com.bank.bank_ia.dto.ApiResponse;
import com.bank.bank_ia.dto.LoanDTO;
import com.bank.bank_ia.dto.LoanOfferDTO;
import com.bank.bank_ia.dto.NewLoanDTO;
import com.bank.bank_ia.dto.NewLoanRequestDTO;
import com.bank.bank_ia.dto.ProfileInvestorDTO;
import com.bank.bank_ia.dto.RefinanceOperationDTO;
import com.bank.bank_ia.dto.RefinanceResponseDTO;
import com.bank.bank_ia.enums.LoanStatus;
import com.bank.bank_ia.services.TransactionService;
import com.bank.bank_ia.services.RefinanceResetService;
import jakarta.validation.Valid;
import com.bank.bank_ia.services.newLoanService;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
@RestController
@RequestMapping("api/v1/bank-ia")
@RequiredArgsConstructor
@Slf4j
public class ClaimController {

    private final ClaimService claimService;
    private final TransactionService transactionService;
    private final LoanService loanService;
    private final RefinanceOperationService refinanceOperationService;
    private final LoanOfferService loanOfferService;
    private final RefinanceResetService refinanceResetService;
    private final newLoanService newLoanService;
    private final ProfileInvestorService profileInvestorService;

    @PostMapping("/claims")
    public ResponseEntity<ClaimDTO> createClaim(
        @RequestBody ClaimRequest claimDTO) 
        {
            ClaimDTO createdClaim = claimService.createClaim(
                claimDTO.customerId(), claimDTO.message()
            );
            return new ResponseEntity<>(createdClaim, HttpStatus.CREATED);


        }

    @GetMapping("/claims/{id}")
    public ResponseEntity<ClaimDTO> getClaimById(@PathVariable UUID id) {
        return ResponseEntity.ok(claimService.getClaimById(id));
    }
    @GetMapping("/loans/{customerId}")
    public ResponseEntity<List<LoanDTO>> getCustomerLoans(@PathVariable String customerId){
        List<LoanDTO> loans = loanService.getLoansByCustomerId(customerId);
        return ResponseEntity.ok(loans);
    }
    
    @GetMapping("/loans/{customerId}/to-cancel")
    public ResponseEntity<List<LoanDTO>> getCustomerRefinances(@PathVariable String customerId){
        List<LoanDTO> loans = loanService.getLoansByCustomerId(customerId);
        // Filtrar solo los préstamos elegibles para refinanciación (ACTIVE y eligibleForRefinance = true)
        List<LoanDTO> eligibleLoans = loans.stream()
            .filter(loan -> LoanStatus.ACTIVE.name().equals(loan.status()) && loan.isEligibleForRefinance())
            .toList();
        return ResponseEntity.ok(eligibleLoans);
    }
    @PostMapping("/refinance") 
    @Transactional
    public ResponseEntity<ApiResponse<RefinanceResponseDTO>> executeRefinance(
            @Valid @RequestBody RefinanceOperationDTO request) {
        log.info("Recibida solicitud de refinanciación para cliente: {}", request.customerId());
        RefinanceResponseDTO response = refinanceOperationService.executeRefinance(request);
        
        return ResponseEntity.ok(ApiResponse.success(response));
    }
    
    @GetMapping("/{customerId}/available-offer")
    public ResponseEntity<List<LoanOfferDTO>> getAvailableOffers(@PathVariable String customerId){
        List<LoanOfferDTO> offers = loanOfferService.getLoanOffersByCustomerId(customerId);
        return ResponseEntity.ok(offers);
    }
    @GetMapping("/transactions/{customerId}")
        public ResponseEntity<List<TransactionDTO>> getCustomerTransactions(@PathVariable String customerId){
            List<TransactionDTO> transactions = transactionService.getCustomerTransactions(customerId);
            
            if (transactions.isEmpty()) {
                return ResponseEntity.notFound().build();
            }
            return ResponseEntity.ok(transactions);
        }
    
    @PostMapping("/reset/{customerId}")
    @Transactional
    public ResponseEntity<ApiResponse<RefinanceResetService.ResetResult>> resetCustomerData(
            @PathVariable String customerId) {
        log.info("Reseteando datos del cliente: {}", customerId);
        
        RefinanceResetService.ResetResult result = refinanceResetService.resetCustomerData(customerId);
        
        return ResponseEntity.ok(ApiResponse.success(result, "Datos reseteados exitosamente"));
    }
    @PostMapping("/new-loan/{customerId}")
    public ResponseEntity<ApiResponse<NewLoanDTO>> createNewLoan(
            @PathVariable String customerId,
            @Valid @RequestBody NewLoanRequestDTO request) {
        log.info("Solicitud de nuevo préstamo para cliente: {}", customerId);
        NewLoanDTO newLoan = newLoanService.createNewLoan(
        new NewLoanDTO(customerId, request.amount(), request.quotas(), request.rate()));
        return new ResponseEntity<>(ApiResponse.success(newLoan), HttpStatus.CREATED);
    }
    @GetMapping("/profile-investor/{customerId}")
    public ResponseEntity<ProfileInvestorDTO> getProfileInvestor(@PathVariable String customerId) {
        Optional<ProfileInvestorDTO> profileInvestor = profileInvestorService.getProfileInvestorByCustomerId(customerId);
        ProfileInvestorDTO body = profileInvestor.orElse(new ProfileInvestorDTO(
            customerId,
            null,
            false,
            null,
            null
        ));
        return ResponseEntity.ok(body);
    }
    @PostMapping("/new-profile-investor/{customerId}")
    public ResponseEntity<ProfileInvestorDTO> createNewProfileInvestor(
        @PathVariable String customerId,
        @Valid @RequestBody ProfileInvestorDTO request) {
        ProfileInvestorDTO profileInvestor = profileInvestorService.createOrUpdateProfile(customerId, request);
        return ResponseEntity.ok(profileInvestor);
    }
    public record ClaimRequest(
        String customerId,
        String message
    ) {}
}