package com.bank.bank_ia.controllers;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import com.bank.bank_ia.dto.RefinanceOperationDTO;
import com.bank.bank_ia.entities.AccountEntity;
import com.bank.bank_ia.entities.LoanEntity;
import com.bank.bank_ia.entities.LoanOfferEntity;
import com.bank.bank_ia.enums.AccountType;
import com.bank.bank_ia.enums.LoanStatus;
import com.bank.bank_ia.repositories.AccountRepository;
import com.bank.bank_ia.repositories.LoanOfferRepository;
import com.bank.bank_ia.repositories.LoanRepository;
import com.fasterxml.jackson.databind.ObjectMapper;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc
@Testcontainers
@DisplayName("ClaimController Integration Tests")
class ClaimControllerIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15-alpine")
            .withDatabaseName("testdb")
            .withUsername("test")
            .withPassword("test");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private LoanRepository loanRepository;

    @Autowired
    private AccountRepository accountRepository;

    @Autowired
    private LoanOfferRepository loanOfferRepository;

    private String customerId;
    private UUID loanId1;
    private UUID loanId2;

    @BeforeEach
    void setUp() {
        loanOfferRepository.deleteAll();
        loanRepository.deleteAll();
        accountRepository.deleteAll();

        customerId = "TEST-CUSTOMER-001";
        loanId1 = UUID.randomUUID();
        loanId2 = UUID.randomUUID();

        // Crear cuenta
        AccountEntity account = new AccountEntity();
        account.setCustomerId(customerId);
        account.setAccountNumber("ACC-TEST-001");
        account.setBalance(new BigDecimal("100000.00"));
        account.setAccountType(AccountType.CHECKING);
        account.setActive(true);
        accountRepository.save(account);

        // Crear préstamos
        LoanEntity loan1 = createLoan(loanId1, customerId, new BigDecimal("200000.00"));
        LoanEntity loan2 = createLoan(loanId2, customerId, new BigDecimal("200000.00"));
        loanRepository.saveAll(List.of(loan1, loan2));

        // Crear oferta que coincida con el request (500000, 60 cuotas, 75% tasa)
        LoanOfferEntity offer = new LoanOfferEntity();
        offer.setId(UUID.randomUUID());
        offer.setCustomerId(customerId);
        offer.setMaxAmount(new BigDecimal("500000.00"));
        offer.setMaxQuotas(60);
        offer.setMonthlyRate(new BigDecimal("75.0"));
        offer.setMinDTI(new BigDecimal("0.3"));
        loanOfferRepository.save(offer);
    }

    @Test
    @DisplayName("Debería ejecutar refinanciación exitosamente")
    void shouldExecuteRefinanceSuccessfully() throws Exception {
        // Given
        RefinanceOperationDTO request = new RefinanceOperationDTO(
            customerId,
            List.of(loanId1, loanId2),
            new BigDecimal("500000.00"),
            60,
            new BigDecimal("75.0"),
            new BigDecimal("100000.00")
        );

        // When/Then
        mockMvc.perform(post("/api/v1/bank-ia/refinance")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.success").value(true))
            .andExpect(jsonPath("$.data.customerId").value(customerId))
            .andExpect(jsonPath("$.data.newLoanId").exists())
            .andExpect(jsonPath("$.data.totalDebtCanceled").value(400000.00))
            .andExpect(jsonPath("$.data.cashOut").value(100000.00));

        // Verificar que los préstamos antiguos fueron cerrados
        LoanEntity closedLoan1 = loanRepository.findById(loanId1).orElseThrow();
        LoanEntity closedLoan2 = loanRepository.findById(loanId2).orElseThrow();
        assertThat(closedLoan1.getStatus()).isEqualTo(LoanStatus.CLOSED_BY_REFINANCE);
        assertThat(closedLoan2.getStatus()).isEqualTo(LoanStatus.CLOSED_BY_REFINANCE);

        // Verificar que se creó el nuevo préstamo
        List<LoanEntity> newLoans = loanRepository.findAllByCustomerId(customerId)
            .stream()
            .filter(loan -> loan.getLoanNumber().startsWith("REF-"))
            .toList();
        assertThat(newLoans).hasSize(1);
    }

    @Test
    @DisplayName("Debería retornar 422 cuando el monto es insuficiente")
    void shouldReturn422WhenAmountIsInsufficient() throws Exception {
        // Given
        RefinanceOperationDTO request = new RefinanceOperationDTO(
            customerId,
            List.of(loanId1, loanId2),
            new BigDecimal("300000.00"), // Insuficiente para cubrir 400000
            60,
            new BigDecimal("75.0"),
            new BigDecimal("100000.00")
        );

        // When/Then (BusinessException -> 422 UNPROCESSABLE_ENTITY)
        mockMvc.perform(post("/api/v1/bank-ia/refinance")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isUnprocessableEntity());
    }

    @Test
    @DisplayName("Debería retornar 422 cuando el monto solicitado supera el máximo de la oferta")
    void shouldReturn422WhenOfferedAmountExceedsOfferMax() throws Exception {
        // Given: oferta tiene maxAmount 500000; solicitamos 600000
        RefinanceOperationDTO request = new RefinanceOperationDTO(
            customerId,
            List.of(loanId1, loanId2),
            new BigDecimal("600000.00"), // Mayor que oferta maxAmount 500000
            60,
            new BigDecimal("75.0"),
            new BigDecimal("200000.00")
        );

        // When/Then (BusinessException -> 422)
        mockMvc.perform(post("/api/v1/bank-ia/refinance")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isUnprocessableEntity());
    }

    @Test
    @DisplayName("Debería retornar 400 cuando la lista de préstamos está vacía")
    void shouldReturn400WhenLoanListIsEmpty() throws Exception {
        // Given (@NotEmpty en sourceLoanIds -> MethodArgumentNotValidException -> 400)
        RefinanceOperationDTO request = new RefinanceOperationDTO(
            customerId,
            List.of(), // Lista vacía
            new BigDecimal("500000.00"),
            60,
            new BigDecimal("75.0"),
            new BigDecimal("100000.00")
        );

        // When/Then
        mockMvc.perform(post("/api/v1/bank-ia/refinance")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isBadRequest());
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
