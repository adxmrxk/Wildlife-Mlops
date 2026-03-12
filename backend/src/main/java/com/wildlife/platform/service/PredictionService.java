package com.wildlife.platform.service;

import com.wildlife.platform.model.Prediction;
import com.wildlife.platform.repository.PredictionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
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

    // Save a prediction — evict stats cache so dashboard shows fresh numbers
    @Transactional
    @CacheEvict(value = "predictionStats", allEntries = true)
    public Prediction savePrediction(Prediction prediction) {
        return predictionRepository.save(prediction);
    }

    // Delete a prediction — evict stats cache
    @Transactional
    @CacheEvict(value = "predictionStats", allEntries = true)
    public void deletePrediction(Long id) {
        predictionRepository.deleteById(id);
    }

    // Save correct species feedback on a prediction
    @Transactional
    public Optional<Prediction> saveFeedback(Long id, String correctSpecies) {
        return predictionRepository.findById(id).map(prediction -> {
            prediction.setCorrectSpecies(correctSpecies);
            return predictionRepository.save(prediction);
        });
    }

    // Delete all predictions — evict stats cache
    @Transactional
    @CacheEvict(value = "predictionStats", allEntries = true)
    public void deleteAllPredictions() {
        predictionRepository.deleteAll();
    }

    // Count total predictions — cached for 1 minute
    @Cacheable("predictionStats")
    public long countPredictions() {
        return predictionRepository.count();
    }

    // Calculate average confidence — cached alongside count in predictionStats
    @Cacheable(value = "predictionStats", key = "'avgConfidence'")
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
