package com.wildlife.platform.dto;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.util.List;

/**
 * DTO for ML service prediction response.
 * Maps the JSON response from the Python ML service.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class MLPredictionResponse {

    private String predicted_species;
    private Double confidence;
    private Boolean is_confident;
    private List<TopPrediction> top_predictions;
    private String model_version;
    private String timestamp;

    /**
     * Inner class for top prediction details.
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TopPrediction {
        private String species;
        private Double confidence;
    }
}
