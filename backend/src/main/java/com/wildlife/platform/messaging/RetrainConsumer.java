package com.wildlife.platform.messaging;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

@Component
public class RetrainConsumer {

    private static final Logger log = LoggerFactory.getLogger(RetrainConsumer.class);
    private static final int RETRAIN_THRESHOLD = 10;

    private final AtomicInteger negativeFeedbackCount = new AtomicInteger(0);
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    public RetrainConsumer(KafkaTemplate<String, String> kafkaTemplate, ObjectMapper objectMapper) {
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
    }

    @KafkaListener(topics = "wildlife.feedback", groupId = "retrain-consumer")
    public void onFeedback(String message) {
        try {
            Map<?, ?> event = objectMapper.readValue(message, Map.class);
            boolean correct = Boolean.TRUE.equals(event.get("correct"));

            if (!correct) {
                int count = negativeFeedbackCount.incrementAndGet();
                log.info("Negative feedback received. Count: {}/{}", count, RETRAIN_THRESHOLD);

                if (count >= RETRAIN_THRESHOLD) {
                    negativeFeedbackCount.set(0);
                    triggerRetrain();
                }
            }
        } catch (Exception e) {
            log.error("Error processing feedback event: {}", e.getMessage());
        }
    }

    private void triggerRetrain() {
        try {
            Map<String, Object> event = Map.of(
                "eventType", "RETRAIN_TRIGGERED",
                "reason", "Negative feedback threshold reached (" + RETRAIN_THRESHOLD + " wrong predictions)",
                "timestamp", Instant.now().toString()
            );
            kafkaTemplate.send("wildlife.retrain", objectMapper.writeValueAsString(event));
            log.info("Retrain triggered — published to wildlife.retrain topic");
        } catch (Exception e) {
            log.error("Failed to publish retrain event: {}", e.getMessage());
        }
    }
}
