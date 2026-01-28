package com.bank.bank_ia.controllers;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
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
import com.bank.bank_ia.services.RefinanceOperationService;
import com.bank.bank_ia.dto.LoanDTO;
import com.bank.bank_ia.dto.LoanOfferDTO;
import com.bank.bank_ia.dto.RefinanceOperationDTO;
import com.bank.bank_ia.services.TransactionService;

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
            .filter(loan -> "ACTIVE".equals(loan.status()) && loan.isEligibleForRefinance())
            .toList();
        return ResponseEntity.ok(eligibleLoans);
    }
    @PostMapping("/refinance") 
    @Transactional
    public ResponseEntity<?> executeRefinance(@RequestBody RefinanceOperationDTO request) {
    try {
        refinanceOperationService.executeRefinance(request);
        
        
        return ResponseEntity.ok(Map.of(
            "message", "Refinanciación exitosa",
            "customerId", request.customerId(),
            "timestamp", LocalDateTime.now()
        )); 
        
    } catch (RuntimeException e) { 
        log.warn("Validación de negocio fallida: {}", e.getMessage());
        return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY).body(e.getMessage());
        
    } catch (Exception e) {
        log.error("Error crítico en refinanciación", e);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                             .body("Ocurrió un error inesperado al procesar tu solicitud.");
    }
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
    public record ClaimRequest(
        String customerId,
        String message
    ) {}
}