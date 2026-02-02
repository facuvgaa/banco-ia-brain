package com.bank.bank_ia.services.impl;

import com.bank.bank_ia.repositories.RefinanceOperationRepository;
import com.bank.bank_ia.services.RefinanceOperationService;
import com.bank.bank_ia.validators.RefinanceValidator;

import java.math.BigDecimal;
import java.util.List;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import com.bank.bank_ia.dto.RefinanceOperationDTO;
import com.bank.bank_ia.dto.RefinanceResponseDTO;
import com.bank.bank_ia.entities.LoanEntity;
import com.bank.bank_ia.entities.LoanOfferEntity;
import com.bank.bank_ia.enums.LoanStatus;
import com.bank.bank_ia.exceptions.InvalidRefinanceException;
import com.bank.bank_ia.repositories.LoanRepository;
import com.bank.bank_ia.repositories.LoanOfferRepository;
import com.bank.bank_ia.services.AccountService;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Slf4j
public class RefinanceOperationServiceImpl implements RefinanceOperationService {

    private final LoanRepository loanRepository;
    private final AccountService accountService;
    private final RefinanceOperationRepository refinanceOperationRepository;
    private final LoanOfferRepository loanOfferRepository;
    private final RefinanceValidator refinanceValidator;
    private final LoanBuilder loanBuilder;

    @Override
    public List<RefinanceOperationDTO> getRefinanceOperationsByCustomerId(String customerId) {
        return refinanceOperationRepository.findByCustomerId(customerId)
                .stream()
                .map(entity -> new RefinanceOperationDTO(
                    entity.getCustomerId(),
                    entity.getSourceLoanIds(),
                    entity.getOfferedAmount(),
                    entity.getSelectedQuotas(),
                    entity.getAppliedRate(),
                    entity.getExpectedCashOut()
                ))
                .collect(Collectors.toList());
    }

    @Override
    @Transactional 
    public RefinanceResponseDTO executeRefinance(RefinanceOperationDTO request) {
        log.info("Iniciando refinanciación para el cliente: {}", request.customerId());
        log.info("Préstamos a refinanciar: {}", request.sourceLoanIds());

        // 1. Obtener ofertas del cliente (antes de borrarlas)
        List<LoanOfferEntity> offers = loanOfferRepository.findAllByCustomerId(request.customerId());
        if (offers.isEmpty()) {
            throw InvalidRefinanceException.noMatchingOffer();
        }

        // 2. Buscar y validar préstamos
        List<LoanEntity> oldLoans = findAndValidateLoans(request);
        BigDecimal totalDebt = calculateTotalDebt(oldLoans);

        // 3. Validar que el monto solicitado esté dentro del rango de la oferta (totalDebt <= offeredAmount <= maxAmount)
        LoanOfferEntity matchingOffer = refinanceValidator.validateAndGetMatchingOffer(request, offers, totalDebt);
        BigDecimal resolvedAmount = matchingOffer.getMaxAmount();

        // 4. Eliminar ofertas del cliente
        deleteCustomerOffers(request.customerId());

        // 5. Calcular cash out con el monto de la oferta en BD (fuente de verdad)
        BigDecimal cashOut = resolvedAmount.subtract(totalDebt);
        log.info("Deuda total a cancelar: {}, Monto oferta (BD): {}, Cash out: {}", totalDebt, resolvedAmount, cashOut);

        // 6. Cerrar préstamos antiguos
        closeOldLoans(oldLoans);

        // 7. Crear nuevo préstamo con el monto resuelto de la oferta
        LoanEntity newLoan = loanBuilder.buildRefinanceLoan(request, resolvedAmount);
        if (newLoan == null) {
            log.error("Error al crear el nuevo préstamo de refinanciación.");
            return null;
        }
        loanRepository.save(newLoan);

        // 8. Acreditar cash out a la cuenta
        creditCashOut(request.customerId(), cashOut, newLoan.getLoanNumber());

        log.info("Refinanciación completada con éxito. Sobrante acreditado: {}", cashOut);

        return RefinanceResponseDTO.of(
            request.customerId(),
            newLoan.getId(),
            newLoan.getLoanNumber(),
            totalDebt,
            cashOut
        );
    }
    
    private void deleteCustomerOffers(String customerId) {
        List<LoanOfferEntity> offers = loanOfferRepository.findAllByCustomerId(customerId);
        if (!offers.isEmpty()) {
            loanOfferRepository.deleteAll(offers);
            log.info("Eliminadas {} ofertas de préstamo para el cliente: {}", offers.size(), customerId);
        }
    }
    
    private List<LoanEntity> findAndValidateLoans(RefinanceOperationDTO request) {
        List<LoanEntity> loans = loanRepository.findAllByIdIn(request.sourceLoanIds());
        log.info("Préstamos encontrados: {} de {} solicitados", loans.size(), request.sourceLoanIds().size());
        
        // Validar usando el validador
        refinanceValidator.validate(request, loans);
        
        return loans;
    }
    
    private BigDecimal calculateTotalDebt(List<LoanEntity> loans) {
        return loans.stream()
            .map(LoanEntity::getRemainingAmount)
            .reduce(BigDecimal.ZERO, BigDecimal::add);
    }
    
    private void closeOldLoans(List<LoanEntity> loans) {
        loans.forEach(loan -> {
            loan.setStatus(LoanStatus.CLOSED_BY_REFINANCE);
            loan.setRemainingAmount(BigDecimal.ZERO);
            loan.setPaidQuotas(loan.getTotalQuotas());
        });
        loanRepository.saveAll(loans);
    }
    
    private void creditCashOut(String customerId, BigDecimal cashOut, String loanNumber) {
        String description = "Crédito por consolidación de deuda - Ref: " + loanNumber;
        log.info("Acreditando sobrante de {} a la cuenta del cliente", cashOut);
        accountService.addBalance(customerId, cashOut, description);
    }
}
