package com.bank.bank_ia.services;

/**
 * Servicio para resetear datos de prueba de clientes.
 * Separado del controller para mantener separación de responsabilidades.
 */
public interface RefinanceResetService {
    /**
     * Resetea los datos de un cliente a su estado inicial de prueba.
     * 
     * @param customerId ID del cliente
     * @return Resumen de la operación de reset
     */
    ResetResult resetCustomerData(String customerId);

    /**
     * Repone en DB el estado demo de FACU-001 / FACU-002 para el cliente de chat (evita drift).
     */
    void ensureFacuDemoLoansIfApplicable(String customerId);

    record ResetResult(
        int restoredLoans,
        int deletedRefinanceLoans,
        int deletedNewLoans,
        int createdOffers
    ) {}
}
