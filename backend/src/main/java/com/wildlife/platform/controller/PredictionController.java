package com.wildlife.platform.controller;

import com.wildlife.platform.model.Prediction;
import com.wildlife.platform.service.PredictionService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/predictions")
@RequiredArgsConstructor
public class PredictionController {

    private final PredictionService predictionService;

    // GET /api/predictions - Get all predictions
    @GetMapping
    public ResponseEntity<List<Prediction>> getAllPredictions() {
        List<Prediction> predictions = predictionService.getAllPredictions();
        return ResponseEntity.ok(predictions);
    }

    // GET /api/predictions/{id} - Get a specific prediction by ID
    @GetMapping("/{id}")
    public ResponseEntity<Prediction> getPredictionById(@PathVariable Long id) {
        return predictionService.getPredictionById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    // GET /api/predictions/species/{speciesId} - Get all predictions for a species
    @GetMapping("/species/{speciesId}")
    public ResponseEntity<List<Prediction>> getPredictionsBySpecies(@PathVariable Long speciesId) {
        List<Prediction> predictions = predictionService.getPredictionsBySpecies(speciesId);
        return ResponseEntity.ok(predictions);
    }

    // GET /api/predictions/model/{version} - Get predictions by model version
    @GetMapping("/model/{version}")
    public ResponseEntity<List<Prediction>> getPredictionsByModel(@PathVariable String version) {
        List<Prediction> predictions = predictionService.getPredictionsByModelVersion(version);
        return ResponseEntity.ok(predictions);
    }

    // POST /api/predictions - Create a new prediction
    @PostMapping
    public ResponseEntity<Prediction> createPrediction(@Valid @RequestBody Prediction prediction) {
        Prediction savedPrediction = predictionService.savePrediction(prediction);
        return ResponseEntity.status(HttpStatus.CREATED).body(savedPrediction);
    }

    // DELETE /api/predictions/{id} - Delete a prediction
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deletePrediction(@PathVariable Long id) {
        return predictionService.getPredictionById(id)
                .map(prediction -> {
                    predictionService.deletePrediction(id);
                    return ResponseEntity.noContent().<Void>build();
                })
                .orElse(ResponseEntity.notFound().build());
    }

    // GET /api/predictions/stats - Get prediction statistics
    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getPredictionStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("total", predictionService.countPredictions());
        stats.put("averageConfidence", predictionService.getAverageConfidence());
        return ResponseEntity.ok(stats);
    }
}
