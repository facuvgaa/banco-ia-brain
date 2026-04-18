package com.bank.bank_ia.services;

import com.bank.bank_ia.dto.ChatRequestDTO;

public interface ChatProducerService {
    void enviarMensaje(ChatRequestDTO request);
}
