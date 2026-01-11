package com.bank.bank_ia.entities;


import java.time.LocalDateTime;
import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import lombok.Data;

@Entity
@Table(name = "claims")
@Data
public class ClaimEntity {
    @Id
    private UUID id;
    
    @Column(nullable = false)
    private String clientId;

    @Column(columnDefinition = "TEXT", nullable = false)
    private String originalMessage;

    @Column(nullable = false)
    private String status;


    @Column(columnDefinition = "TEXT")
    private String category;

    @Column(updatable = false)
    private LocalDateTime dataCreation;

    @PrePersist
    protected void onCreate() {
        this.dataCreation = LocalDateTime.now();
        if (this.id == null) {
            this.id = UUID.randomUUID();
        }
    }

    @Column(columnDefinition = "TEXT") 
    private String resolution;

    
}