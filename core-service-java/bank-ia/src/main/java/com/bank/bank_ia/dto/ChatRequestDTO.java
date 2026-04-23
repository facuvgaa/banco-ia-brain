package com.bank.bank_ia.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class ChatRequestDTO {
    private String contenido;

    private String contexto;

    @NotNull
    private String customerId;
}
