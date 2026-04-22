package com.bank.bank_ia.kafka;

import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import com.bank.bank_ia.chat.ChatWebSocketRegistry;
import com.bank.bank_ia.dto.ChatReplyPayload;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Component
@Slf4j
@RequiredArgsConstructor
public class ChatResponseListener {

    private final ObjectMapper objectMapper;
    private final ChatWebSocketRegistry chatWebSocketRegistry;

    @KafkaListener(topics = "chat-response", groupId = "bank-ia-chat-response", concurrency = "1")
    public void onChatResponse(String message) {
        try {
            ChatReplyPayload payload = objectMapper.readValue(message, ChatReplyPayload.class);
            if (payload.customerId() == null || payload.customerId().isBlank()) {
                log.warn("chat-response sin customerId: {}", message);
                return;
            }
            log.info("💬 Reenviando respuesta a cliente (WebSocket) {}", payload.customerId());
            chatWebSocketRegistry.sendReply(payload.customerId().trim(), payload.reply());
        } catch (JsonProcessingException e) {
            log.error("No se pudo parsear chat-response: {}", message, e);
        }
    }
}
