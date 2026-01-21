package com.bank.bank_ia.entities;

import java.math.BigDecimal;
import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Data;

@Data
@Entity
@Table(name = "refinances")
public class RefinanceEntity {
    @Id
    private UUID id;

    @Column(nullable = false)
    private String loadNumber;

    @Column(nullable = false)
    private BigDecimal remainingAmount;

    @Column(nullable = false)
    private Integer paidQuotas;

    @Column(nullable = false)
    private BigDecimal monthlyQuota;

    @Column(nullable = false)
    private Boolean canBeRefinanced;
}
