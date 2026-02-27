package com.wildlife.platform.service;

import com.wildlife.platform.dto.MLPredictionResponse;
import com.wildlife.platform.model.Species;
import com.wildlife.platform.repository.SpeciesRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;

import java.io.File;

/**
 * Service for communicating with the ML prediction service.
 */
@Service
public class MLPredictionService {

    @Value("${ml.service.url}")
    private String mlServiceUrl;

    @Value("${ml.service.timeout:30000}")
    private int timeout;

    @Value("${prediction.auto-create-species:true}")
    private boolean autoCreateSpecies;

    private final RestTemplate restTemplate;
    private final SpeciesRepository speciesRepository;

    public MLPredictionService(SpeciesRepository speciesRepository) {
        this.speciesRepository = speciesRepository;
        this.restTemplate = new RestTemplate();
    }

    /**
     * Predict species from image file using ML service.
     *
     * @param imageFile Image file to predict
     * @return ML prediction response
     * @throws RuntimeException If ML service call fails
     */
    public MLPredictionResponse predict(File imageFile) {
        String predictUrl = mlServiceUrl + "/predict";

        try {
            // Prepare multipart request
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.MULTIPART_FORM_DATA);

            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            body.add("image", new FileSystemResource(imageFile));

            HttpEntity<MultiValueMap<String, Object>> requestEntity =
                    new HttpEntity<>(body, headers);

            // Call ML service
            ResponseEntity<MLPredictionResponse> response = restTemplate.exchange(
                    predictUrl,
                    HttpMethod.POST,
                    requestEntity,
                    MLPredictionResponse.class
            );

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                return response.getBody();
            } else {
                throw new RuntimeException("ML service returned empty response");
            }

        } catch (ResourceAccessException e) {
            // ML service not reachable
            throw new RuntimeException(
                    "ML service is unavailable. Please ensure the ML service is running on " +
                            mlServiceUrl, e
            );
        } catch (HttpClientErrorException e) {
            // 4xx errors (bad request, invalid image, etc.)
            String errorMessage = "ML service rejected the request: " + e.getResponseBodyAsString();
            throw new RuntimeException(errorMessage, e);
        } catch (HttpServerErrorException e) {
            // 5xx errors (model inference failure, etc.)
            String errorMessage = "ML service encountered an error: " + e.getResponseBodyAsString();
            throw new RuntimeException(errorMessage, e);
        } catch (Exception e) {
            throw new RuntimeException("Unexpected error calling ML service: " + e.getMessage(), e);
        }
    }

    /**
     * Resolve species by name. Auto-creates species if enabled and not found.
     *
     * @param speciesName Species name from ML prediction
     * @return Species entity
     * @throws RuntimeException If species not found and auto-create disabled
     */
    public Species resolveSpecies(String speciesName) {
        return speciesRepository.findByName(speciesName)
                .orElseGet(() -> {
                    if (autoCreateSpecies) {
                        // Auto-create new species
                        Species newSpecies = Species.builder()
                                .name(speciesName)
                                .commonName(speciesName)
                                .description("Auto-created from ML prediction")
                                .active(true)
                                .build();

                        Species saved = speciesRepository.save(newSpecies);
                        System.out.println("Auto-created new species: " + speciesName + " (ID: " + saved.getId() + ")");
                        return saved;
                    } else {
                        throw new RuntimeException(
                                "Species '" + speciesName + "' not found in database. " +
                                        "Auto-create is disabled. Please add this species manually."
                        );
                    }
                });
    }

    /**
     * Check if ML service is available.
     *
     * @return true if ML service responds to health check
     */
    public boolean isMLServiceAvailable() {
        try {
            String healthUrl = mlServiceUrl + "/health";
            ResponseEntity<String> response = restTemplate.getForEntity(healthUrl, String.class);
            return response.getStatusCode() == HttpStatus.OK;
        } catch (Exception e) {
            return false;
        }
    }
}
