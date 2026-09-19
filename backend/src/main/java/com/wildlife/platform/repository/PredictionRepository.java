package com.wildlife.platform.repository;

import com.wildlife.platform.model.Prediction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface PredictionRepository extends JpaRepository<Prediction, Long> {

    // Find all predictions for a specific species
    List<Prediction> findByPredictedSpeciesId(Long speciesId);

    // Find all predictions made by a specific model version
    List<Prediction> findByModelVersion(String modelVersion);

    // Predictions the model was unsure about and nobody has corrected yet —
    // the human-in-the-loop review queue. Lowest confidence first.
    List<Prediction> findByConfidenceLessThanAndCorrectSpeciesIsNullOrderByConfidenceAsc(
            Double confidence);

    // Predictions a human has already labelled — the feedback training set.
    List<Prediction> findByCorrectSpeciesIsNotNull();

    // JpaRepository also gives us:
    // - save(Prediction) - save a prediction
    // - findById(Long) - find by ID
    // - findAll() - get all predictions
    // - deleteById(Long) - delete a prediction
    // - count() - count total predictions
}
