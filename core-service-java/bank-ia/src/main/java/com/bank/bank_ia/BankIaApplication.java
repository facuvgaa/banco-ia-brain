package com.bank.bank_ia;

import com.bank.bank_ia.entities.TransactionEntity;
import com.bank.bank_ia.repositories.TransactionRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Objects;

@SpringBootApplication
public class BankIaApplication {

    public static void main(String[] args) {
        SpringApplication.run(BankIaApplication.class, args);
    }

    @Bean
    CommandLineRunner seedTransactions(TransactionRepository repository) {
        return args -> {
            // Verificamos si ya hay datos para no duplicar en cada reinicio
            if (repository.count() == 0) {
                // Registro 1: Una transferencia que falló (ideal para que el Brain la encuentre)
                repository.save(Objects.requireNonNull(TransactionEntity.builder()
                        .customerId("BERNARDO-001")
                        .amount(new BigDecimal("55000.00"))
                        .currency("ARS")
                        .status("FAILED")
                        .transactionDate(LocalDateTime.now().minusHours(2))
                        .description("Transferencia enviada a CBU 00000234...")
                        .build()));

                // Registro 2: Un gasto común completado
                repository.save(Objects.requireNonNull(TransactionEntity.builder()
                        .customerId("BERNARDO-001")
                        .amount(new BigDecimal("4500.00"))
                        .currency("ARS")
                        .status("COMPLETED")
                        .transactionDate(LocalDateTime.now().minusDays(1))
                        .description("Compra en Supermercado")
                        .build()));

                System.out.println("✅ Datos de prueba de transacciones insertados en Postgres.");
            }
        };
    }
}