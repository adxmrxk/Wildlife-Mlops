package com.wildlife.platform.messaging;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import java.util.Map;

/**
 * Consumes the wildlife.retrain topic.
 *
 * RetrainConsumer publishes a RETRAIN_TRIGGERED event once enough predictions
 * have been marked wrong, but nothing was listening, so the signal went
 * nowhere. This records each signal so the dashboard can surface "retraining
 * recommended" to an operator.
 *
 * Deliberately does NOT kick off training itself: a training run takes hours
 * on CPU and would replace the live model without anyone reviewing it.
 * Promotion stays a human decision.
 */
@Component
public class RetrainSignalConsumer {

    private static final Logger log = LoggerFactory.getLogger(RetrainSignalConsumer.class);
    private static final int MAX_RETAINED = 50;

    private final ObjectMapper objectMapper;
    private final Deque<Map<String, Object>> signals = new ArrayDeque<>();

    public RetrainSignalConsumer(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @KafkaListener(topics = "wildlife.retrain", groupId = "retrain-signal-recorder")
    public void onRetrainSignal(String message) {
        try {
            Map<?, ?> event = objectMapper.readValue(message, Map.class);
            Map<String, Object> record = Map.of(
                    "reason", String.valueOf(event.get("reason")),
                    "eventType", String.valueOf(event.get("eventType")),
                    "triggeredAt", String.valueOf(event.get("timestamp")),
                    "recordedAt", Instant.now().toString()
            );
            synchronized (signals) {
                signals.addFirst(record);
                while (signals.size() > MAX_RETAINED) {
                    signals.removeLast();
                }
            }
            log.info("Retrain signal recorded: {}", record.get("reason"));
        } catch (Exception e) {
            log.error("Error processing retrain signal: {}", e.getMessage());
        }
    }

    /** Most recent retrain signals, newest first. */
    public List<Map<String, Object>> getSignals() {
        synchronized (signals) {
            return new ArrayList<>(signals);
        }
    }
}
