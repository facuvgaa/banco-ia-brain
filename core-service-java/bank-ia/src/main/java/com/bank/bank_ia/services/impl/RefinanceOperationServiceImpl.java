package com.bank.bank_ia.services.impl;

import com.bank.bank_ia.repositories.RefinanceOperationRepository;
import com.bank.bank_ia.services.RefinanceOperationService;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import com.bank.bank_ia.dto.RefinanceOperationDTO;
import com.bank.bank_ia.entities.LoanEntity;
import com.bank.bank_ia.entities.LoanOfferEntity;
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
    public void executeRefinance(RefinanceOperationDTO request) {
        log.info("Iniciando refinanciación para el cliente: {}", request.customerId());

        // Eliminar todas las ofertas de préstamo del cliente
        List<LoanOfferEntity> offers = loanOfferRepository.findAllByCustomerId(request.customerId());
        if (!offers.isEmpty()) {
            loanOfferRepository.deleteAll(offers);
            log.info("Eliminadas {} ofertas de préstamo para el cliente: {}", offers.size(), request.customerId());
        }

        List<LoanEntity> oldLoans = loanRepository.findAllByCustomerId(request.customerId());

        if (oldLoans.isEmpty()) {
            throw new RuntimeException("No se encontraron préstamos válidos para refinanciar.");
        }

        BigDecimal totalDebtToCancel = oldLoans.stream()
                .map(LoanEntity::getRemainingAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        log.info("Deuda total a cancelar: {}", totalDebtToCancel);

        BigDecimal calculatedCashOut = request.offeredAmount().subtract(totalDebtToCancel);

        if (calculatedCashOut.compareTo(BigDecimal.ZERO) < 0) {
            throw new RuntimeException("El monto ofrecido no cubre la deuda actual.");
        }

        oldLoans.forEach(loan -> {
            loan.setStatus("CLOSED_BY_REFINANCE");
            loan.setRemainingAmount(BigDecimal.ZERO);
            loan.setPaidQuotas(loan.getTotalQuotas()); // Se marcan como completados
        });

        loanRepository.saveAll(oldLoans);

        LoanEntity newLoan = new LoanEntity();
        newLoan.setCustomerId(request.customerId());
        newLoan.setLoanNumber("REF-" + System.currentTimeMillis());
        newLoan.setTotalAmount(request.offeredAmount());
        newLoan.setRemainingAmount(request.offeredAmount());
        newLoan.setQuotaAmount(request.offeredAmount().divide(new BigDecimal(request.selectedQuotas())));
        newLoan.setTotalQuotas(request.selectedQuotas());
        newLoan.setPaidQuotas(0);
        newLoan.setStatus("ACTIVE");
        newLoan.setStartDate(LocalDateTime.now());
        
        loanRepository.save(newLoan);

        String description = "Crédito por consolidación de deuda - Ref: " + newLoan.getLoanNumber();
        accountService.addBalance(request.customerId(), calculatedCashOut, description);

        log.info("Refinanciación completada con éxito. Sobrante acreditado: {}", calculatedCashOut);
    }
}
