package com.bank.bank_ia.chat;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.springframework.stereotype.Service;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;

import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

/**
 * Reenvía respuestas de Kafka (chat-response) al navegador por WebSocket, por {@code customerId}.
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class ChatWebSocketRegistry {

    private final ObjectMapper objectMapper;

    private final ConcurrentHashMap<String, WebSocketSession> sessions = new ConcurrentHashMap<>();

    private static String normId(String customerId) {
        return customerId == null ? "" : customerId.trim();
    }

    public void register(String customerId, WebSocketSession session) {
        String id = normId(customerId);
        WebSocketSession previous = sessions.put(id, session);
        if (previous != null) {
            try {
                if (previous.isOpen()) {
                    previous.close();
                }
            } catch (IOException e) {
                log.debug("Cerrar sesión WS anterior customerId={}: {}", id, e.getMessage());
            }
        }
        log.info("WebSocket conectado customerId={}", id);
    }

    public void unregister(String customerId, WebSocketSession session) {
        String id = normId(customerId);
        sessions.remove(id, session);
    }

    public void sendReply(String customerId, String reply) {
        String id = normId(customerId);
        WebSocketSession session = sessions.get(id);
        if (session == null || !session.isOpen()) {
            log.warn(
                    "chat-response de Kafka sin cliente WebSocket (¿WS abierto y mismo customerId?): '{}'",
                    id);
            return;
        }
        try {
            String json =
                    objectMapper.writeValueAsString(
                            Map.of("type", "reply", "text", reply == null ? "" : reply));
            session.sendMessage(new TextMessage(json));
        } catch (IOException e) {
            log.error("Error enviando WebSocket a {}", id, e);
            sessions.remove(id, session);
            try {
                session.close();
            } catch (IOException ignored) {
            }
        }
    }
}
