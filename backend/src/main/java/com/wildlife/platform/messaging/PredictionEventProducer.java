package com.wildlife.platform.messaging;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.wildlife.platform.model.Prediction;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.Map;

@Component
public class PredictionEventProducer {

    private static final Logger log = LoggerFactory.getLogger(PredictionEventProducer.class);

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    public PredictionEventProducer(KafkaTemplate<String, String> kafkaTemplate, ObjectMapper objectMapper) {
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
    }

    public void publishPredictionEvent(Prediction prediction) {
        try {
            Map<String, Object> event = Map.of(
                "eventType", "PREDICTION_MADE",
                "predictionId", prediction.getId(),
                "species", prediction.getPredictedSpecies() != null ? prediction.getPredictedSpecies().getName() : "unknown",
                "confidence", prediction.getConfidence(),
                "timestamp", Instant.now().toString()
            );
            kafkaTemplate.send("wildlife.predictions", String.valueOf(prediction.getId()), objectMapper.writeValueAsString(event));
            log.info("Published prediction event for id={}", prediction.getId());
        } catch (Exception e) {
            log.warn("Failed to publish prediction event: {}", e.getMessage());
        }
    }

    public void publishFeedbackEvent(Long predictionId, boolean correct, String correctSpecies) {
        try {
            Map<String, Object> event = Map.of(
                "eventType", "FEEDBACK_SUBMITTED",
                "predictionId", predictionId,
                "correct", correct,
                "correctSpecies", correctSpecies != null ? correctSpecies : "",
                "timestamp", Instant.now().toString()
            );
            kafkaTemplate.send("wildlife.feedback", String.valueOf(predictionId), objectMapper.writeValueAsString(event));
            log.info("Published feedback event for predictionId={}, correct={}", predictionId, correct);
        } catch (Exception e) {
            log.warn("Failed to publish feedback event: {}", e.getMessage());
        }
    }
}
