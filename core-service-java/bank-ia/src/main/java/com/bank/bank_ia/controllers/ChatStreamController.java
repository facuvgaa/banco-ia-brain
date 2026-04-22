package com.bank.bank_ia.controllers;

import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import com.bank.bank_ia.chat.ChatSseRegistry;

import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api/chat")
@CrossOrigin(origins = "http://localhost:5173")
@RequiredArgsConstructor
public class ChatStreamController {

    private final ChatSseRegistry chatSseRegistry;

    @GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter subscribe(@RequestParam("customerId") String customerId) {
        if (customerId == null) {
            customerId = "";
        } else {
            customerId = customerId.trim();
        }
        return chatSseRegistry.register(customerId);
    }
}
