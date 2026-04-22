package com.bank.bank_ia.controllers;

import java.util.HashMap;
import java.util.Map;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.bank.bank_ia.dto.ChatRequestDTO;
import com.bank.bank_ia.services.ChatProducerService;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "http://localhost:5173")
public class ChatController {

    @Autowired
    private ChatProducerService producerService;

    @PostMapping("/chat")
    public ResponseEntity<Map<String, Object>> handleChat(@RequestBody ChatRequestDTO request) {

        producerService.enviarMensaje(request);

        Map<String, Object> response = new HashMap<>();
        response.put("queued", true);
        return ResponseEntity.accepted().body(response);
    }
}
