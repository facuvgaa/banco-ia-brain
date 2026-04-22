package com.bank.bank_ia.chat;

import org.springframework.lang.NonNull;
import org.springframework.stereotype.Component;

import com.bank.bank_ia.config.CustomerIdHandshakeInterceptor;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.WebSocketMessage;
import org.springframework.web.socket.WebSocketSession;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

/**
 * Suscribe la sesión al {@link ChatWebSocketRegistry} (customerId vía query en el handshake).
 */
@Component
@Slf4j
@RequiredArgsConstructor
public class ChatWebSocketHandler implements WebSocketHandler {

    private final ChatWebSocketRegistry chatWebSocketRegistry;

    @Override
    public void afterConnectionEstablished(@NonNull WebSocketSession session) {
        String customerId =
                (String) session.getAttributes().get(CustomerIdHandshakeInterceptor.ATTR_CUSTOMER_ID);
        if (customerId == null || customerId.isBlank()) {
            try {
                session.close(CloseStatus.NOT_ACCEPTABLE.withReason("customerId requerido"));
            } catch (Exception e) {
                log.debug("Cerrar WS sin customerId: {}", e.getMessage());
            }
            return;
        }
        chatWebSocketRegistry.register(customerId, session);
    }

    @Override
    public void handleMessage(
            @NonNull WebSocketSession session, @NonNull WebSocketMessage<?> message) {
        // No se usa por ahora: las respuestas vienen de Kafka. Ignorar pings del cliente.
        if (message instanceof TextMessage text) {
            log.trace("Mensaje WS recibido (ignorado) customerId={}: {}", customerIdOrDash(session), text);
        }
    }

    @Override
    public void handleTransportError(
            @NonNull WebSocketSession session, @NonNull Throwable exception) {
        log.debug("Error transporte WS customerId={}: {}", customerIdOrDash(session), exception.getMessage());
    }

    @Override
    public void afterConnectionClosed(
            @NonNull WebSocketSession session, @NonNull CloseStatus closeStatus) {
        String customerId =
                (String) session.getAttributes().get(CustomerIdHandshakeInterceptor.ATTR_CUSTOMER_ID);
        if (customerId != null) {
            chatWebSocketRegistry.unregister(customerId, session);
        }
        log.info("WebSocket desconectado status={} customerId={}", closeStatus, customerId);
    }

    @Override
    public boolean supportsPartialMessages() {
        return false;
    }

    private static String customerIdOrDash(WebSocketSession session) {
        Object c = session.getAttributes().get(CustomerIdHandshakeInterceptor.ATTR_CUSTOMER_ID);
        return c == null ? "—" : c.toString();
    }
}
