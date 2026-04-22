package com.bank.bank_ia.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record ChatReplyPayload(
        @JsonProperty("customerId") String customerId,
        @JsonProperty("reply") String reply) {
}
