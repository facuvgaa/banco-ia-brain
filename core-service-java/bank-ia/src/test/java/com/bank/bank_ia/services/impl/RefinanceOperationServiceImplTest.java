package com.bank.bank_ia.services.impl;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.bank.bank_ia.dto.RefinanceOperationDTO;
import com.bank.bank_ia.dto.RefinanceResponseDTO;
import com.bank.bank_ia.entities.LoanEntity;
import com.bank.bank_ia.entities.LoanOfferEntity;
import com.bank.bank_ia.enums.LoanStatus;
import com.bank.bank_ia.exceptions.InvalidRefinanceException;
import com.bank.bank_ia.repositories.LoanOfferRepository;
import com.bank.bank_ia.repositories.LoanRepository;
import com.bank.bank_ia.repositories.RefinanceOperationRepository;
import com.bank.bank_ia.services.AccountService;
import com.bank.bank_ia.validators.RefinanceValidator;

@ExtendWith(MockitoExtension.class)
@DisplayName("RefinanceOperationServiceImpl Tests")
class RefinanceOperationServiceImplTest {

    @Mock
    private LoanRepository loanRepository;

    @Mock
    private AccountService accountService;

    @Mock
    private RefinanceOperationRepository refinanceOperationRepository;

    @Mock
    private LoanOfferRepository loanOfferRepository;

    @Mock
    private RefinanceValidator refinanceValidator;

    @Mock
    private LoanBuilder loanBuilder;

    @InjectMocks
    private RefinanceOperationServiceImpl service;

    private String customerId;
    private UUID loanId1;
    private UUID loanId2;
    private RefinanceOperationDTO request;
    private List<LoanEntity> oldLoans;
    private LoanEntity newLoan;

    @BeforeEach
    void setUp() {
        customerId = "CUSTOMER-001";
        loanId1 = UUID.randomUUID();
        loanId2 = UUID.randomUUID();

        request = new RefinanceOperationDTO(
            customerId,
            List.of(loanId1, loanId2),
            new BigDecimal("500000.00"),
            60,
            new BigDecimal("75.0"),
            new BigDecimal("100000.00")
        );

        oldLoans = List.of(
            createLoan(loanId1, customerId, new BigDecimal("200000.00")),
            createLoan(loanId2, customerId, new BigDecimal("200000.00"))
        );

        newLoan = new LoanEntity();
        newLoan.setId(UUID.randomUUID());
        newLoan.setLoanNumber("REF-123456");
        newLoan.setCustomerId(customerId);
        newLoan.setTotalAmount(new BigDecimal("500000.00"));
        newLoan.setRemainingAmount(new BigDecimal("500000.00"));
        newLoan.setQuotaAmount(new BigDecimal("8333.33"));
        newLoan.setPaidQuotas(0);
        newLoan.setTotalQuotas(60);
        newLoan.setStatus(LoanStatus.ACTIVE);
        newLoan.setStartDate(LocalDateTime.now());
        newLoan.setEligibleForRefinance(false);
    }

    @Test
    @DisplayName("Debería ejecutar refinanciación exitosamente")
    void shouldExecuteRefinanceSuccessfully() {
        // Given
        List<LoanOfferEntity> offers = List.of(new LoanOfferEntity());
        
        when(loanOfferRepository.findAllByCustomerId(customerId)).thenReturn(offers);
        when(loanRepository.findAllByIdIn(anyList())).thenReturn(oldLoans);
        doNothing().when(refinanceValidator).validate(any(), anyList());
        when(loanBuilder.buildRefinanceLoan(request)).thenReturn(newLoan);
        when(loanRepository.save(any(LoanEntity.class))).thenReturn(newLoan);
        doNothing().when(accountService).addBalance(anyString(), any(BigDecimal.class), anyString());

        // When
        RefinanceResponseDTO response = service.executeRefinance(request);

        // Then
        assertThat(response).isNotNull();
        assertThat(response.customerId()).isEqualTo(customerId);
        assertThat(response.newLoanId()).isEqualTo(newLoan.getId());
        assertThat(response.totalDebtCanceled()).isEqualByComparingTo(new BigDecimal("400000.00"));
        assertThat(response.cashOut()).isEqualByComparingTo(new BigDecimal("100000.00"));

        verify(loanOfferRepository).findAllByCustomerId(customerId);
        verify(loanOfferRepository).deleteAll(offers);
        verify(loanRepository).findAllByIdIn(request.sourceLoanIds());
        verify(refinanceValidator).validate(request, oldLoans);
        verify(loanRepository).saveAll(oldLoans);
        verify(loanRepository).save(newLoan);
        verify(accountService).addBalance(customerId, new BigDecimal("100000.00"), anyString());
    }

    @Test
    @DisplayName("Debería eliminar ofertas del cliente antes de refinanciar")
    void shouldDeleteCustomerOffers() {
        // Given
        List<LoanOfferEntity> offers = List.of(
            new LoanOfferEntity(),
            new LoanOfferEntity()
        );
        
        when(loanOfferRepository.findAllByCustomerId(customerId)).thenReturn(offers);
        when(loanRepository.findAllByIdIn(anyList())).thenReturn(oldLoans);
        doNothing().when(refinanceValidator).validate(any(), anyList());
        when(loanBuilder.buildRefinanceLoan(request)).thenReturn(newLoan);
        when(loanRepository.save(any(LoanEntity.class))).thenReturn(newLoan);
        doNothing().when(accountService).addBalance(anyString(), any(BigDecimal.class), anyString());

        // When
        service.executeRefinance(request);

        // Then
        verify(loanOfferRepository).deleteAll(offers);
    }

    @Test
    @DisplayName("Debería cerrar préstamos antiguos con estado CLOSED_BY_REFINANCE")
    void shouldCloseOldLoans() {
        // Given
        when(loanOfferRepository.findAllByCustomerId(customerId)).thenReturn(new ArrayList<>());
        when(loanRepository.findAllByIdIn(anyList())).thenReturn(oldLoans);
        doNothing().when(refinanceValidator).validate(any(), anyList());
        when(loanBuilder.buildRefinanceLoan(request)).thenReturn(newLoan);
        when(loanRepository.save(any(LoanEntity.class))).thenReturn(newLoan);
        doNothing().when(accountService).addBalance(anyString(), any(BigDecimal.class), anyString());

        // When
        service.executeRefinance(request);

        // Then
        assertThat(oldLoans.get(0).getStatus()).isEqualTo(LoanStatus.CLOSED_BY_REFINANCE);
        assertThat(oldLoans.get(0).getRemainingAmount()).isEqualByComparingTo(BigDecimal.ZERO);
        assertThat(oldLoans.get(1).getStatus()).isEqualTo(LoanStatus.CLOSED_BY_REFINANCE);
        assertThat(oldLoans.get(1).getRemainingAmount()).isEqualByComparingTo(BigDecimal.ZERO);
        verify(loanRepository).saveAll(oldLoans);
    }

    @Test
    @DisplayName("Debería lanzar excepción cuando la validación falla")
    void shouldThrowExceptionWhenValidationFails() {
        // Given
        when(loanOfferRepository.findAllByCustomerId(customerId)).thenReturn(new ArrayList<>());
        when(loanRepository.findAllByIdIn(anyList())).thenReturn(oldLoans);
        org.mockito.Mockito.doThrow(new InvalidRefinanceException("Validación fallida"))
            .when(refinanceValidator).validate(any(RefinanceOperationDTO.class), anyList());

        // When/Then
        assertThatThrownBy(() -> service.executeRefinance(request))
            .isInstanceOf(InvalidRefinanceException.class)
            .hasMessageContaining("Validación fallida");

        verify(loanRepository, never()).save(any(LoanEntity.class));
        verify(accountService, never()).addBalance(anyString(), any(BigDecimal.class), anyString());
    }

    @Test
    @DisplayName("Debería calcular cash out correctamente")
    void shouldCalculateCashOutCorrectly() {
        // Given
        BigDecimal offeredAmount = new BigDecimal("500000.00");
        BigDecimal totalDebt = new BigDecimal("400000.00");
        BigDecimal expectedCashOut = new BigDecimal("100000.00");

        request = new RefinanceOperationDTO(
            customerId,
            List.of(loanId1, loanId2),
            offeredAmount,
            60,
            new BigDecimal("75.0"),
            expectedCashOut
        );

        when(loanOfferRepository.findAllByCustomerId(customerId)).thenReturn(new ArrayList<>());
        when(loanRepository.findAllByIdIn(anyList())).thenReturn(oldLoans);
        doNothing().when(refinanceValidator).validate(any(), anyList());
        when(loanBuilder.buildRefinanceLoan(request)).thenReturn(newLoan);
        when(loanRepository.save(any(LoanEntity.class))).thenReturn(newLoan);
        doNothing().when(accountService).addBalance(anyString(), any(BigDecimal.class), anyString());

        // When
        RefinanceResponseDTO response = service.executeRefinance(request);

        // Then
        assertThat(response.cashOut()).isEqualByComparingTo(expectedCashOut);
        verify(accountService).addBalance(customerId, expectedCashOut, anyString());
    }

    private LoanEntity createLoan(UUID id, String customerId, BigDecimal remainingAmount) {
        LoanEntity loan = new LoanEntity();
        loan.setId(id);
        loan.setCustomerId(customerId);
        loan.setLoanNumber("LOAN-" + id.toString().substring(0, 8));
        loan.setTotalAmount(remainingAmount.multiply(new BigDecimal("2")));
        loan.setRemainingAmount(remainingAmount);
        loan.setQuotaAmount(new BigDecimal("10000.00"));
        loan.setPaidQuotas(0);
        loan.setTotalQuotas(10);
        loan.setStatus(LoanStatus.ACTIVE);
        loan.setStartDate(LocalDateTime.now());
        loan.setEligibleForRefinance(true);
        return loan;
    }
}
