package com.bank.bank_ia.config;

import java.util.Map;

import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.http.server.ServletServerHttpRequest;
import org.springframework.lang.NonNull;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.server.HandshakeInterceptor;

/**
 * Pasa {@code customerId} del query string al atributo de la sesión WebSocket.
 */
public class CustomerIdHandshakeInterceptor implements HandshakeInterceptor {

    public static final String ATTR_CUSTOMER_ID = "customerId";

    @Override
    public boolean beforeHandshake(
            @NonNull ServerHttpRequest request,
            @NonNull ServerHttpResponse response,
            @NonNull WebSocketHandler wsHandler,
            @NonNull Map<String, Object> attributes) {
        if (request instanceof ServletServerHttpRequest servlet) {
            String q = servlet.getServletRequest().getParameter("customerId");
            if (q == null || q.isBlank()) {
                return false;
            }
            attributes.put(ATTR_CUSTOMER_ID, q.trim());
            return true;
        }
        return false;
    }

    @Override
    public void afterHandshake(
            @NonNull ServerHttpRequest request,
            @NonNull ServerHttpResponse response,
            @NonNull WebSocketHandler wsHandler,
            Exception exception) {
        // no-op
    }
}
