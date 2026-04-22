package com.bank.bank_ia.chat;

import java.io.IOException;
import java.util.concurrent.ConcurrentHashMap;

import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import lombok.extern.slf4j.Slf4j;

@Service
@Slf4j
public class ChatSseRegistry {

    private final ConcurrentHashMap<String, SseEmitter> emitters = new ConcurrentHashMap<>();

    private static String normId(String customerId) {
        return customerId == null ? "" : customerId.trim();
    }

    public SseEmitter register(String customerId) {
        String id = normId(customerId);
        SseEmitter emitter = new SseEmitter(0L);
        SseEmitter previous = emitters.put(id, emitter);
        if (previous != null) {
            previous.complete();
        }
        Runnable remove = () -> emitters.remove(id, emitter);
        emitter.onCompletion(remove);
        emitter.onTimeout(remove);
        emitter.onError(e -> remove.run());
        try {
            // Comentario SSE: mantiene viva la conexión y ayuda a algunos proxys/browsers
            emitter.send(SseEmitter.event().comment("moustro-sse-ok"));
        } catch (IOException e) {
            log.warn("No se pudo enviar comentario inicial SSE: {}", e.getMessage());
        }
        log.info("SSE conectado customerId={}", id);
        return emitter;
    }

    /**
     * Usa el evento por defecto (tipo "message") — compatible con eventSource.onmessage
     * y con EventSource bajo CORS; evitá solo addEventListener("reply", ...).
     */
    public void sendReply(String customerId, String reply) {
        String id = normId(customerId);
        SseEmitter emitter = emitters.get(id);
        if (emitter == null) {
            log.warn("chat-response Kafka pero no hay suscriptor SSE (¿SSE abierto y mismo customerId?): '{}'", id);
            return;
        }
        try {
            // Nombre "message" explícito: máxima compatibilidad con EventSource.onmessage
            emitter.send(
                    SseEmitter.event()
                            .name("message")
                            .data(reply == null ? "" : reply, MediaType.TEXT_PLAIN));
        } catch (IOException e) {
            log.error("Error enviando evento SSE a {}", id, e);
            emitters.remove(id, emitter);
            emitter.completeWithError(e);
        }
    }
}
