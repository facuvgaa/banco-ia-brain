package com.bank.bank_ia.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.lang.NonNull;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

import com.bank.bank_ia.chat.ChatWebSocketHandler;

import lombok.RequiredArgsConstructor;

/**
 * WebSocket bajo /api (mismo prefijo CORS del front en 5173) para reenviar respuestas de Kafka.
 */
@Configuration
@EnableWebSocket
@RequiredArgsConstructor
public class WebSocketConfig implements WebSocketConfigurer {

    private final ChatWebSocketHandler chatWebSocketHandler;

    @Override
    public void registerWebSocketHandlers(@NonNull WebSocketHandlerRegistry registry) {
        registry
                .addHandler(chatWebSocketHandler, "/api/chat/ws")
                .addInterceptors(new CustomerIdHandshakeInterceptor())
                .setAllowedOrigins("http://localhost:5173", "http://127.0.0.1:5173");
    }
}
