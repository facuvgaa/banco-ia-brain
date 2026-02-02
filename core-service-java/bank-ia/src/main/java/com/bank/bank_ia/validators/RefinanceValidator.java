package com.bank.bank_ia.validators;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

import org.springframework.stereotype.Component;

import com.bank.bank_ia.dto.RefinanceOperationDTO;
import com.bank.bank_ia.entities.LoanEntity;
import com.bank.bank_ia.entities.LoanOfferEntity;
import com.bank.bank_ia.exceptions.InvalidRefinanceException;
import com.bank.bank_ia.exceptions.LoanNotFoundException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Component
@RequiredArgsConstructor
@Slf4j
public class RefinanceValidator {
    
    /**
     * Valida que la solicitud de refinanciación sea válida.
     * 
     * @param request La solicitud de refinanciación
     * @param loans Los préstamos encontrados en la base de datos
     * @throws InvalidRefinanceException Si la validación falla
     */
    public void validate(RefinanceOperationDTO request, List<LoanEntity> loans) {
        validateLoanList(request.sourceLoanIds());
        validateLoansFound(loans, request.sourceLoanIds());
        validateLoanOwnership(loans, request.customerId());
        validateAmount(request.offeredAmount(), calculateTotalDebt(loans));
    }
    
    private void validateLoanList(List<UUID> loanIds) {
        if (loanIds == null || loanIds.isEmpty()) {
            throw InvalidRefinanceException.emptyLoanList();
        }
    }
    
    private void validateLoansFound(List<LoanEntity> foundLoans, List<UUID> requestedIds) {
        if (foundLoans.isEmpty()) {
            throw new LoanNotFoundException(requestedIds);
        }
        
        if (foundLoans.size() != requestedIds.size()) {
            log.warn("Se encontraron {} préstamos de {} solicitados", foundLoans.size(), requestedIds.size());
        }
    }
    
    private void validateLoanOwnership(List<LoanEntity> loans, String customerId) {
        for (LoanEntity loan : loans) {
            if (!loan.getCustomerId().equals(customerId)) {
                throw InvalidRefinanceException.loanNotBelongsToCustomer(loan.getId(), customerId);
            }
        }
    }
    
    private void validateAmount(BigDecimal offeredAmount, BigDecimal totalDebt) {
        BigDecimal cashOut = offeredAmount.subtract(totalDebt);
        if (cashOut.compareTo(BigDecimal.ZERO) < 0) {
            throw InvalidRefinanceException.insufficientAmount(offeredAmount, totalDebt);
        }
    }
    
    private BigDecimal calculateTotalDebt(List<LoanEntity> loans) {
        return loans.stream()
            .map(LoanEntity::getRemainingAmount)
            .reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    /**
     * Valida que el monto solicitado esté dentro del rango permitido por la oferta del cliente.
     * El monto debe ser: totalDebt <= offeredAmount <= maxAmount de la oferta que coincida con cuotas y tasa.
     *
     * @param request Solicitud de refinanciación
     * @param offers Ofertas vigentes del cliente
     * @param totalDebt Deuda total a cancelar
     * @return La oferta que coincide con la solicitud (cuotas y tasa)
     * @throws InvalidRefinanceException Si no hay oferta coincidente o el monto está fuera de rango
     */
    public LoanOfferEntity validateAndGetMatchingOffer(
            RefinanceOperationDTO request,
            List<LoanOfferEntity> offers,
            BigDecimal totalDebt) {
        if (offers == null || offers.isEmpty()) {
            throw InvalidRefinanceException.noMatchingOffer();
        }

        LoanOfferEntity matching = offers.stream()
            .filter(o -> Integer.valueOf(o.getMaxQuotas()).equals(request.selectedQuotas())
                && o.getMonthlyRate().compareTo(request.appliedRate()) == 0)
            .findFirst()
            .orElseThrow(InvalidRefinanceException::noMatchingOffer);

        BigDecimal maxAmount = matching.getMaxAmount();
        BigDecimal offered = request.offeredAmount();

        if (offered.compareTo(totalDebt) < 0) {
            throw InvalidRefinanceException.insufficientAmount(offered, totalDebt);
        }
        if (offered.compareTo(maxAmount) > 0) {
            throw InvalidRefinanceException.offeredAmountOutOfRange(offered, totalDebt, maxAmount);
        }

        return matching;
    }
}
