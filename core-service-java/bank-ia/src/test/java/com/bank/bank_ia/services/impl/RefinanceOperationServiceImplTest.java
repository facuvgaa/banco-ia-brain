package com.bank.bank_ia.services.impl;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
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

    private LoanOfferEntity createMatchingOffer() {
        LoanOfferEntity offer = new LoanOfferEntity();
        offer.setId(UUID.randomUUID());
        offer.setCustomerId(customerId);
        offer.setMaxAmount(new BigDecimal("500000.00"));
        offer.setMaxQuotas(60);
        offer.setMonthlyRate(new BigDecimal("75.0"));
        offer.setMinDTI(new BigDecimal("0.3"));
        return offer;
    }

    @Test
    @DisplayName("Debería ejecutar refinanciación exitosamente")
    void shouldExecuteRefinanceSuccessfully() {
        // Given
        LoanOfferEntity matchingOffer = createMatchingOffer();
        List<LoanOfferEntity> offers = List.of(matchingOffer);

        when(loanOfferRepository.findAllByCustomerId(customerId)).thenReturn(offers);
        when(loanRepository.findAllByIdIn(anyList())).thenReturn(oldLoans);
        doNothing().when(refinanceValidator).validate(any(), anyList());
        when(refinanceValidator.validateAndGetMatchingOffer(any(), anyList(), any())).thenReturn(matchingOffer);
        when(loanBuilder.buildRefinanceLoan(eq(request), eq(new BigDecimal("500000.00")))).thenReturn(newLoan);
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

        verify(loanOfferRepository, times(2)).findAllByCustomerId(customerId);
        verify(loanOfferRepository).deleteAll(offers);
        verify(loanRepository).findAllByIdIn(request.sourceLoanIds());
        verify(refinanceValidator).validate(request, oldLoans);
        verify(refinanceValidator).validateAndGetMatchingOffer(eq(request), eq(offers), eq(new BigDecimal("400000.00")));
        verify(loanRepository).saveAll(oldLoans);
        verify(loanBuilder).buildRefinanceLoan(eq(request), eq(new BigDecimal("500000.00")));
        verify(loanRepository).save(newLoan);
        verify(accountService).addBalance(eq(customerId), eq(new BigDecimal("100000.00")), anyString());
    }

    @Test
    @DisplayName("Debería eliminar ofertas del cliente antes de refinanciar")
    void shouldDeleteCustomerOffers() {
        // Given
        LoanOfferEntity matchingOffer = createMatchingOffer();
        List<LoanOfferEntity> offers = List.of(matchingOffer, new LoanOfferEntity());

        when(loanOfferRepository.findAllByCustomerId(customerId)).thenReturn(offers);
        when(loanRepository.findAllByIdIn(anyList())).thenReturn(oldLoans);
        doNothing().when(refinanceValidator).validate(any(), anyList());
        when(refinanceValidator.validateAndGetMatchingOffer(any(), anyList(), any())).thenReturn(matchingOffer);
        when(loanBuilder.buildRefinanceLoan(any(), any(BigDecimal.class))).thenReturn(newLoan);
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
        LoanOfferEntity matchingOffer = createMatchingOffer();
        List<LoanOfferEntity> offers = List.of(matchingOffer);

        when(loanOfferRepository.findAllByCustomerId(customerId)).thenReturn(offers);
        when(loanRepository.findAllByIdIn(anyList())).thenReturn(oldLoans);
        doNothing().when(refinanceValidator).validate(any(), anyList());
        when(refinanceValidator.validateAndGetMatchingOffer(any(), anyList(), any())).thenReturn(matchingOffer);
        when(loanBuilder.buildRefinanceLoan(any(), any(BigDecimal.class))).thenReturn(newLoan);
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
    @DisplayName("Debería lanzar excepción cuando no hay ofertas")
    void shouldThrowExceptionWhenNoOffers() {
        // Given
        when(loanOfferRepository.findAllByCustomerId(customerId)).thenReturn(new ArrayList<>());

        // When/Then
        assertThatThrownBy(() -> service.executeRefinance(request))
            .isInstanceOf(InvalidRefinanceException.class)
            .hasMessageContaining("No se encontró una oferta");

        verify(loanRepository, never()).save(any(LoanEntity.class));
        verify(accountService, never()).addBalance(anyString(), any(BigDecimal.class), anyString());
    }

    @Test
    @DisplayName("Debería lanzar excepción cuando la validación de préstamos falla")
    void shouldThrowExceptionWhenLoanValidationFails() {
        // Given
        List<LoanOfferEntity> offers = List.of(createMatchingOffer());
        when(loanOfferRepository.findAllByCustomerId(customerId)).thenReturn(offers);
        when(loanRepository.findAllByIdIn(anyList())).thenReturn(oldLoans);
        doThrow(new InvalidRefinanceException("Validación fallida"))
            .when(refinanceValidator).validate(any(RefinanceOperationDTO.class), anyList());

        // When/Then
        assertThatThrownBy(() -> service.executeRefinance(request))
            .isInstanceOf(InvalidRefinanceException.class)
            .hasMessageContaining("Validación fallida");

        verify(loanRepository, never()).save(any(LoanEntity.class));
        verify(accountService, never()).addBalance(anyString(), any(BigDecimal.class), anyString());
    }

    @Test
    @DisplayName("Debería calcular cash out con monto de la oferta en BD")
    void shouldCalculateCashOutCorrectly() {
        // Given: oferta con maxAmount 500000, deuda 400000 -> cash out 100000
        LoanOfferEntity matchingOffer = createMatchingOffer();
        List<LoanOfferEntity> offers = List.of(matchingOffer);
        BigDecimal expectedCashOut = new BigDecimal("100000.00");

        when(loanOfferRepository.findAllByCustomerId(customerId)).thenReturn(offers);
        when(loanRepository.findAllByIdIn(anyList())).thenReturn(oldLoans);
        doNothing().when(refinanceValidator).validate(any(), anyList());
        when(refinanceValidator.validateAndGetMatchingOffer(any(), anyList(), any())).thenReturn(matchingOffer);
        when(loanBuilder.buildRefinanceLoan(any(), eq(new BigDecimal("500000.00")))).thenReturn(newLoan);
        when(loanRepository.save(any(LoanEntity.class))).thenReturn(newLoan);
        doNothing().when(accountService).addBalance(anyString(), any(BigDecimal.class), anyString());

        // When
        RefinanceResponseDTO response = service.executeRefinance(request);

        // Then: cash out = oferta.maxAmount - totalDebt = 500000 - 400000 = 100000
        assertThat(response.cashOut()).isEqualByComparingTo(expectedCashOut);
        verify(accountService).addBalance(eq(customerId), eq(expectedCashOut), anyString());
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
