package com.bank.bank_ia.config;

import java.math.BigDecimal;
import java.math.RoundingMode;

/**
 * Constantes relacionadas con préstamos.
 * Centraliza valores que se usan en múltiples lugares.
 */
public final class LoanConstants {
    
    private LoanConstants() {
        // Utility class
    }
    
    // Prefijos para números de préstamo
    public static final String REFINANCE_LOAN_PREFIX = "REF-";
    public static final String STANDARD_LOAN_PREFIX = "LOAN-";
    
    // Configuración de cálculos
    public static final int QUOTA_DECIMAL_SCALE = 2;
    public static final RoundingMode QUOTA_ROUNDING_MODE = RoundingMode.HALF_UP;
    
    // Valores por defecto
    public static final BigDecimal DEFAULT_INITIAL_BALANCE = new BigDecimal("100000.00");
    
    // Configuración de préstamos de prueba (debería moverse a properties)
    public static final class TestLoans {
        public static final String LOAN_001 = "LOAN-001";
        public static final String LOAN_002 = "LOAN-002";
        public static final String LOAN_003 = "LOAN-003";
        public static final String LOAN_004 = "LOAN-004";
        public static final String LOAN_005 = "LOAN-005";
        
        private TestLoans() {}
    }
}
