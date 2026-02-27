package com.wildlife.platform.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import lombok.Data;

import jakarta.annotation.PostConstruct;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Configuration for file storage settings.
 */
@Configuration
@ConfigurationProperties(prefix = "file")
@Data
public class FileStorageConfig {

    /**
     * Base directory for file uploads (e.g., "./uploads")
     */
    private String uploadDir = "./uploads";

    /**
     * Maximum file size in bytes (default: 10MB)
     */
    private long maxSize = 10485760; // 10MB in bytes

    /**
     * Allowed file types (comma-separated)
     */
    private String allowedTypes = "jpg,jpeg,png";

    /**
     * Initialize upload directory on startup.
     */
    @PostConstruct
    public void init() {
        try {
            Path uploadPath = Paths.get(uploadDir).toAbsolutePath().normalize();
            Files.createDirectories(uploadPath);

            // Create predictions subdirectory
            Path predictionsPath = uploadPath.resolve("predictions");
            Files.createDirectories(predictionsPath);

            System.out.println("Upload directories initialized:");
            System.out.println("  Base: " + uploadPath);
            System.out.println("  Predictions: " + predictionsPath);
        } catch (IOException e) {
            throw new RuntimeException("Could not create upload directory!", e);
        }
    }

    /**
     * Get upload directory as a Path object.
     */
    @Bean
    public Path uploadPath() {
        return Paths.get(uploadDir).toAbsolutePath().normalize();
    }
}
