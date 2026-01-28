package com.bank.bank_ia.validators;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import com.bank.bank_ia.dto.RefinanceOperationDTO;
import com.bank.bank_ia.entities.LoanEntity;
import com.bank.bank_ia.enums.LoanStatus;
import com.bank.bank_ia.exceptions.InvalidRefinanceException;
import com.bank.bank_ia.exceptions.LoanNotFoundException;

@DisplayName("RefinanceValidator Tests")
class RefinanceValidatorTest {

    private RefinanceValidator validator;
    private String customerId;
    private UUID loanId1;
    private UUID loanId2;

    @BeforeEach
    void setUp() {
        validator = new RefinanceValidator();
        customerId = "CUSTOMER-001";
        loanId1 = UUID.randomUUID();
        loanId2 = UUID.randomUUID();
    }

    @Test
    @DisplayName("Debería validar correctamente una solicitud válida")
    void shouldValidateValidRequest() {
        // Given
        RefinanceOperationDTO request = new RefinanceOperationDTO(
            customerId,
            List.of(loanId1, loanId2),
            new BigDecimal("500000.00"),
            60,
            new BigDecimal("75.0"),
            new BigDecimal("100000.00")
        );

        List<LoanEntity> loans = List.of(
            createLoan(loanId1, customerId, new BigDecimal("200000.00")),
            createLoan(loanId2, customerId, new BigDecimal("200000.00"))
        );

        // When/Then
        assertThat(validator).isNotNull();
        validator.validate(request, loans);
    }

    @Test
    @DisplayName("Debería lanzar excepción cuando la lista de préstamos está vacía")
    void shouldThrowExceptionWhenLoanListIsEmpty() {
        // Given
        RefinanceOperationDTO request = new RefinanceOperationDTO(
            customerId,
            new ArrayList<>(),
            new BigDecimal("500000.00"),
            60,
            new BigDecimal("75.0"),
            new BigDecimal("100000.00")
        );

        List<LoanEntity> loans = new ArrayList<>();

        // When/Then
        assertThatThrownBy(() -> validator.validate(request, loans))
            .isInstanceOf(InvalidRefinanceException.class)
            .hasMessageContaining("lista de préstamos");
    }

    @Test
    @DisplayName("Debería lanzar excepción cuando la lista de préstamos es null")
    void shouldThrowExceptionWhenLoanListIsNull() {
        // Given
        RefinanceOperationDTO request = new RefinanceOperationDTO(
            customerId,
            null,
            new BigDecimal("500000.00"),
            60,
            new BigDecimal("75.0"),
            new BigDecimal("100000.00")
        );

        List<LoanEntity> loans = new ArrayList<>();

        // When/Then
        assertThatThrownBy(() -> validator.validate(request, loans))
            .isInstanceOf(InvalidRefinanceException.class);
    }

    @Test
    @DisplayName("Debería lanzar excepción cuando no se encuentran préstamos")
    void shouldThrowExceptionWhenNoLoansFound() {
        // Given
        RefinanceOperationDTO request = new RefinanceOperationDTO(
            customerId,
            List.of(loanId1, loanId2),
            new BigDecimal("500000.00"),
            60,
            new BigDecimal("75.0"),
            new BigDecimal("100000.00")
        );

        List<LoanEntity> loans = new ArrayList<>();

        // When/Then
        assertThatThrownBy(() -> validator.validate(request, loans))
            .isInstanceOf(LoanNotFoundException.class);
    }

    @Test
    @DisplayName("Debería lanzar excepción cuando un préstamo no pertenece al cliente")
    void shouldThrowExceptionWhenLoanNotBelongsToCustomer() {
        // Given
        RefinanceOperationDTO request = new RefinanceOperationDTO(
            customerId,
            List.of(loanId1),
            new BigDecimal("500000.00"),
            60,
            new BigDecimal("75.0"),
            new BigDecimal("100000.00")
        );

        List<LoanEntity> loans = List.of(
            createLoan(loanId1, "OTHER-CUSTOMER", new BigDecimal("200000.00"))
        );

        // When/Then
        assertThatThrownBy(() -> validator.validate(request, loans))
            .isInstanceOf(InvalidRefinanceException.class)
            .hasMessageContaining("no pertenece");
    }

    @Test
    @DisplayName("Debería lanzar excepción cuando el monto ofrecido es insuficiente")
    void shouldThrowExceptionWhenAmountIsInsufficient() {
        // Given
        RefinanceOperationDTO request = new RefinanceOperationDTO(
            customerId,
            List.of(loanId1, loanId2),
            new BigDecimal("300000.00"), // Menor que la deuda total (400000)
            60,
            new BigDecimal("75.0"),
            new BigDecimal("100000.00")
        );

        List<LoanEntity> loans = List.of(
            createLoan(loanId1, customerId, new BigDecimal("200000.00")),
            createLoan(loanId2, customerId, new BigDecimal("200000.00"))
        );

        // When/Then
        assertThatThrownBy(() -> validator.validate(request, loans))
            .isInstanceOf(InvalidRefinanceException.class)
            .hasMessageContaining("insuficiente");
    }

    @Test
    @DisplayName("Debería validar correctamente cuando el monto ofrecido es exactamente igual a la deuda")
    void shouldValidateWhenAmountEqualsDebt() {
        // Given
        BigDecimal debt = new BigDecimal("400000.00");
        RefinanceOperationDTO request = new RefinanceOperationDTO(
            customerId,
            List.of(loanId1, loanId2),
            debt, // Exactamente igual a la deuda
            60,
            new BigDecimal("75.0"),
            BigDecimal.ZERO
        );

        List<LoanEntity> loans = List.of(
            createLoan(loanId1, customerId, new BigDecimal("200000.00")),
            createLoan(loanId2, customerId, new BigDecimal("200000.00"))
        );

        // When/Then
        assertThat(validator).isNotNull();
        validator.validate(request, loans);
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
        loan.setEligibleForRefinance(true);
        return loan;
    }
}
