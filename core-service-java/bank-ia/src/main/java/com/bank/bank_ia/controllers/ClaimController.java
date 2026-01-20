package com.bank.bank_ia.controllers;

import java.util.List;
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
import com.bank.bank_ia.services.LoanService;
import com.bank.bank_ia.dto.LoanDTO;
import com.bank.bank_ia.services.TransactionService;

import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("api/v1/bank-ia")
@RequiredArgsConstructor
public class ClaimController {

    private final ClaimService claimService;
    private final TransactionService transactionService;
    private final LoanService loanService;


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