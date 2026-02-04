package com.bank.bank_ia.entities;
import java.math.BigDecimal;
import java.util.UUID;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Data;

@Entity
@Table(name = "loan_offers")
@Data
public class LoanOfferEntity {
    @Id
    private UUID id;
    @Column(nullable = false)
    private String customerId;
    @Column(nullable = false)   
    private BigDecimal maxAmount;
    @Column(nullable = false)
    private Integer maxQuotas;
    @Column(nullable = false)
    private BigDecimal monthlyRate;
    @Column(nullable = false)
    private BigDecimal minDTI;
    
}
