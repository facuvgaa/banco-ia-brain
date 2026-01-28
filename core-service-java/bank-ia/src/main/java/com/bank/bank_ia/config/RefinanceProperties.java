package com.bank.bank_ia.config;

import java.math.BigDecimal;
import java.math.RoundingMode;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import lombok.Getter;
import lombok.Setter;

/**
 * Propiedades de configuración para refinanciaciones.
 * Los valores pueden ser sobrescritos desde application.properties
 */
@Configuration
@ConfigurationProperties(prefix = "refinance")
@Getter
@Setter
public class RefinanceProperties {
    
    /**
     * Prefijo para números de préstamos de refinanciación.
     */
    private String loanPrefix = "REF-";
    
    /**
     * Escala decimal para cálculos de cuotas.
     */
    private int quotaDecimalScale = 2;
    
    /**
     * Modo de redondeo para cálculos de cuotas.
     */
    private RoundingMode quotaRoundingMode = RoundingMode.HALF_UP;
    
    /**
     * Tiempo mínimo (en días) antes de que un préstamo sea elegible para refinanciación.
     */
    private int minDaysBeforeRefinance = 0;
    
    /**
     * Monto mínimo para refinanciación.
     */
    private BigDecimal minRefinanceAmount = new BigDecimal("100000.00");
}
