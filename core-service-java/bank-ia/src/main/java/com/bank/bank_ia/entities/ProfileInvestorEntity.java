package com.bank.bank_ia.entities;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Data;

import java.util.UUID;

@Entity
@Table(name = "profile_investor")
@Data
public class ProfileInvestorEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false)
    private String customerId;

    @Column(nullable = true)
    private String riskLevel;

    @Column(nullable = false)
    private Boolean hasProfile;

    @Column(nullable = true)
    private Integer maxLossPercent;

    @Column(nullable = true)
    private String horizon;
}
