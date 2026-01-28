package com.bank.bank_ia.services.impl;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.List;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import com.bank.bank_ia.config.RefinanceProperties;
import com.bank.bank_ia.dto.RefinanceOperationDTO;
import com.bank.bank_ia.entities.LoanEntity;
import com.bank.bank_ia.enums.LoanStatus;

@DisplayName("LoanBuilder Tests")
class LoanBuilderTest {

    private LoanBuilder loanBuilder;
    private RefinanceProperties properties;

    @BeforeEach
    void setUp() {
        properties = new RefinanceProperties();
        properties.setLoanPrefix("REF-");
        properties.setQuotaDecimalScale(2);
        properties.setQuotaRoundingMode(RoundingMode.HALF_UP);
        loanBuilder = new LoanBuilder(properties);
    }

    @Test
    @DisplayName("Debería crear un préstamo de refinanciación con todos los campos correctos")
    void shouldBuildRefinanceLoanWithAllFields() {
        // Given
        RefinanceOperationDTO request = new RefinanceOperationDTO(
            "CUSTOMER-001",
            List.of(),
            new BigDecimal("1000000.00"),
            60,
            new BigDecimal("75.0"),
            new BigDecimal("100000.00")
        );

        // When
        LoanEntity loan = loanBuilder.buildRefinanceLoan(request);

        // Then
        assertThat(loan).isNotNull();
        assertThat(loan.getId()).isNotNull();
        assertThat(loan.getCustomerId()).isEqualTo("CUSTOMER-001");
        assertThat(loan.getLoanNumber()).startsWith("REF-");
        assertThat(loan.getTotalAmount()).isEqualByComparingTo(new BigDecimal("1000000.00"));
        assertThat(loan.getRemainingAmount()).isEqualByComparingTo(new BigDecimal("1000000.00"));
        assertThat(loan.getTotalQuotas()).isEqualTo(60);
        assertThat(loan.getPaidQuotas()).isEqualTo(0);
        assertThat(loan.getStatus()).isEqualTo(LoanStatus.ACTIVE);
        assertThat(loan.getStartDate()).isNotNull();
        assertThat(loan.getStartDate()).isBeforeOrEqualTo(LocalDateTime.now());
        assertThat(loan.isEligibleForRefinance()).isFalse();
    }

    @Test
    @DisplayName("Debería calcular correctamente el monto de cuota")
    void shouldCalculateQuotaAmountCorrectly() {
        // Given
        RefinanceOperationDTO request = new RefinanceOperationDTO(
            "CUSTOMER-001",
            List.of(),
            new BigDecimal("1000000.00"),
            60,
            new BigDecimal("75.0"),
            new BigDecimal("100000.00")
        );

        // When
        LoanEntity loan = loanBuilder.buildRefinanceLoan(request);

        // Then
        BigDecimal expectedQuota = new BigDecimal("1000000.00")
            .divide(new BigDecimal("60"), 2, RoundingMode.HALF_UP);
        assertThat(loan.getQuotaAmount()).isEqualByComparingTo(expectedQuota);
    }

    @Test
    @DisplayName("Debería generar números de préstamo únicos")
    void shouldGenerateUniqueLoanNumbers() {
        // Given
        RefinanceOperationDTO request = new RefinanceOperationDTO(
            "CUSTOMER-001",
            List.of(),
            new BigDecimal("1000000.00"),
            60,
            new BigDecimal("75.0"),
            new BigDecimal("100000.00")
        );

        // When
        LoanEntity loan1 = loanBuilder.buildRefinanceLoan(request);
        try {
            Thread.sleep(1); // Asegurar timestamp diferente
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        LoanEntity loan2 = loanBuilder.buildRefinanceLoan(request);

        // Then
        assertThat(loan1.getLoanNumber()).isNotEqualTo(loan2.getLoanNumber());
        assertThat(loan1.getLoanNumber()).startsWith("REF-");
        assertThat(loan2.getLoanNumber()).startsWith("REF-");
    }

    @Test
    @DisplayName("Debería usar el prefijo configurado en properties")
    void shouldUseConfiguredPrefix() {
        // Given
        properties.setLoanPrefix("CUSTOM-REF-");
        loanBuilder = new LoanBuilder(properties);
        
        RefinanceOperationDTO request = new RefinanceOperationDTO(
            "CUSTOMER-001",
            List.of(),
            new BigDecimal("1000000.00"),
            60,
            new BigDecimal("75.0"),
            new BigDecimal("100000.00")
        );

        // When
        LoanEntity loan = loanBuilder.buildRefinanceLoan(request);

        // Then
        assertThat(loan.getLoanNumber()).startsWith("CUSTOM-REF-");
    }
}
