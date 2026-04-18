package com.bank.bank_ia.services.impl;

import java.util.Objects;

import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

import com.bank.bank_ia.dto.ChatRequestDTO;
import com.bank.bank_ia.services.ChatProducerService;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Service
@Slf4j
@RequiredArgsConstructor
public class ChatProducerServiceImpl implements ChatProducerService {

    private final KafkaTemplate<String, ChatRequestDTO> kafkaTemplate;

    @Override
    public void enviarMensaje(ChatRequestDTO request) {
        String customerId = Objects.requireNonNullElse(request.getCustomerId(), "anonymous");
        log.info("Publicando mensaje de {} en chat-queries", customerId);
        kafkaTemplate.send("chat-queries", customerId, request);
    }
}
