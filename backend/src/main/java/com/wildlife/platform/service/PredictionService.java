package com.wildlife.platform.service;

import com.wildlife.platform.model.Prediction;
import com.wildlife.platform.repository.PredictionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class PredictionService {

    private final PredictionRepository predictionRepository;

    // Get all predictions
    public List<Prediction> getAllPredictions() {
        return predictionRepository.findAll();
    }

    // Get a specific prediction by ID
    public Optional<Prediction> getPredictionById(Long id) {
        return predictionRepository.findById(id);
    }

    // Get all predictions for a specific species
    public List<Prediction> getPredictionsBySpecies(Long speciesId) {
        return predictionRepository.findByPredictedSpeciesId(speciesId);
    }

    // Get all predictions from a specific model version
    public List<Prediction> getPredictionsByModelVersion(String modelVersion) {
        return predictionRepository.findByModelVersion(modelVersion);
    }

    // Save a prediction
    @Transactional
    public Prediction savePrediction(Prediction prediction) {
        return predictionRepository.save(prediction);
    }

    // Delete a prediction
    @Transactional
    public void deletePrediction(Long id) {
        predictionRepository.deleteById(id);
    }

    // Count total predictions
    public long countPredictions() {
        return predictionRepository.count();
    }

    // Calculate average confidence across all predictions
    public Double getAverageConfidence() {
        List<Prediction> predictions = predictionRepository.findAll();
        if (predictions.isEmpty()) {
            return 0.0;
        }
        return predictions.stream()
                .mapToDouble(Prediction::getConfidence)
                .average()
                .orElse(0.0);
    }
}
