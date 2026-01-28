package com.bank.bank_ia.dto;

import java.time.LocalDateTime;

/**
 * Wrapper genérico para respuestas de API.
 * Proporciona un formato consistente para todas las respuestas.
 * 
 * @param <T> Tipo de datos de la respuesta
 */
public record ApiResponse<T>(
    boolean success,
    T data,
    String message,
    LocalDateTime timestamp
) {
    public static <T> ApiResponse<T> success(T data) {
        return new ApiResponse<>(true, data, "Operación exitosa", LocalDateTime.now());
    }
    
    public static <T> ApiResponse<T> success(T data, String message) {
        return new ApiResponse<>(true, data, message, LocalDateTime.now());
    }
    
    public static <T> ApiResponse<T> error(String message) {
        return new ApiResponse<>(false, null, message, LocalDateTime.now());
    }
}
