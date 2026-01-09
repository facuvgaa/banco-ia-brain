package com.bank.bank_ia.dto;


import java.util.UUID;
import java.io.Serializable;

public record ClaimDTO(
    UUID id,
    String customerId,
    String message,
    String status,
    String category
) implements Serializable {}
