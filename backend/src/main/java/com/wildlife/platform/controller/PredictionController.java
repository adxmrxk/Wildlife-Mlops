package com.wildlife.platform.controller;

import com.wildlife.platform.dto.MLPredictionResponse;
import com.wildlife.platform.messaging.PredictionEventProducer;
import com.wildlife.platform.model.Prediction;
import com.wildlife.platform.model.Species;
import com.wildlife.platform.service.FileStorageService;
import com.wildlife.platform.service.MLPredictionService;
import com.wildlife.platform.service.PredictionService;
import com.wildlife.platform.service.S3StorageService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/predictions")
@RequiredArgsConstructor
public class PredictionController {

    private final PredictionService predictionService;
    private final MLPredictionService mlPredictionService;
    private final FileStorageService fileStorageService;
    private final S3StorageService s3StorageService;
    private final PredictionEventProducer eventProducer;

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

    // POST /api/predictions/upload - Upload image and predict species
    @PostMapping("/upload")
    public ResponseEntity<?> uploadAndPredict(@RequestParam("image") MultipartFile file) {
        Path tempFile = null;
        try {
            // 1. Validate file
            fileStorageService.validateFile(file);

            // 2. Upload to S3/MinIO (cloud object storage)
            String imageUrl = s3StorageService.uploadFile(file, "predictions");

            // 3. Write to a temp file so ML service can read it from disk
            tempFile = Files.createTempFile("wildlife_", "_" + file.getOriginalFilename());
            Files.copy(file.getInputStream(), tempFile, StandardCopyOption.REPLACE_EXISTING);

            // 4. Call ML service for prediction
            MLPredictionResponse mlResponse = mlPredictionService.predict(tempFile.toFile());

            // 5. Resolve species (auto-create if needed)
            Species species = mlPredictionService.resolveSpecies(mlResponse.getPredicted_species());

            // 6. Build Prediction entity with S3 URL
            Prediction prediction = Prediction.builder()
                    .imageName(file.getOriginalFilename())
                    .imageUrl(imageUrl)
                    .predictedSpecies(species)
                    .confidence(mlResponse.getConfidence())
                    .modelVersion(mlResponse.getModel_version())
                    .build();

            // 7. Save to database
            Prediction savedPrediction = predictionService.savePrediction(prediction);

            // 8. Attach GradCAM heatmap (transient — not stored in DB)
            savedPrediction.setHeatmapBase64(mlResponse.getHeatmap_base64());

            // 9. Publish prediction event to Kafka
            eventProducer.publishPredictionEvent(savedPrediction);

            // 10. Return response
            return ResponseEntity.status(HttpStatus.CREATED).body(savedPrediction);

        } catch (IllegalArgumentException e) {
            Map<String, String> error = new HashMap<>();
            error.put("error", e.getMessage());

            if (e.getMessage().contains("size exceeds")) {
                return ResponseEntity.status(HttpStatus.PAYLOAD_TOO_LARGE).body(error);
            } else if (e.getMessage().contains("Invalid file type") || e.getMessage().contains("Invalid content type")) {
                return ResponseEntity.status(HttpStatus.UNSUPPORTED_MEDIA_TYPE).body(error);
            } else {
                return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(error);
            }

        } catch (RuntimeException e) {
            Map<String, String> error = new HashMap<>();
            error.put("error", e.getMessage());

            if (e.getMessage() != null && (e.getMessage().contains("unavailable") || e.getMessage().contains("not reachable"))) {
                return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(error);
            } else if (e.getMessage() != null && e.getMessage().contains("timeout")) {
                return ResponseEntity.status(HttpStatus.GATEWAY_TIMEOUT).body(error);
            } else {
                return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(error);
            }

        } catch (Exception e) {
            Map<String, String> error = new HashMap<>();
            error.put("error", "An unexpected error occurred: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(error);

        } finally {
            // Clean up temp file
            if (tempFile != null) {
                try { Files.deleteIfExists(tempFile); } catch (Exception ignored) {}
            }
        }
    }

    // PATCH /api/predictions/{id}/feedback - Submit correct species feedback
    @PatchMapping("/{id}/feedback")
    public ResponseEntity<?> submitFeedback(@PathVariable Long id, @RequestBody Map<String, String> body) {
        String correctSpecies = body.get("correctSpecies");
        if (correctSpecies == null || correctSpecies.isBlank()) {
            return ResponseEntity.badRequest().body(Map.of("error", "correctSpecies is required"));
        }
        return predictionService.saveFeedback(id, correctSpecies)
                .map(saved -> {
                    boolean correct = saved.getPredictedSpecies() != null &&
                        saved.getPredictedSpecies().getName().equalsIgnoreCase(correctSpecies);
                    eventProducer.publishFeedbackEvent(id, correct, correctSpecies);
                    return ResponseEntity.ok(saved);
                })
                .orElse(ResponseEntity.notFound().build());
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

    // DELETE /api/predictions - Delete all predictions
    @DeleteMapping
    public ResponseEntity<Void> deleteAllPredictions() {
        predictionService.deleteAllPredictions();
        return ResponseEntity.noContent().build();
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
