package com.wildlife.platform.service;

import com.wildlife.platform.config.FileStorageConfig;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Arrays;
import java.util.List;

/**
 * Service for handling file storage operations.
 */
@Service
public class FileStorageService {

    private final FileStorageConfig fileStorageConfig;
    private final Path uploadPath;

    public FileStorageService(FileStorageConfig fileStorageConfig, Path uploadPath) {
        this.fileStorageConfig = fileStorageConfig;
        this.uploadPath = uploadPath;
    }

    /**
     * Save uploaded file to the specified subdirectory.
     *
     * @param file         Uploaded file
     * @param subdirectory Subdirectory within upload directory (e.g., "predictions")
     * @return Absolute path to saved file
     * @throws IOException If file save fails
     */
    public String saveFile(MultipartFile file, String subdirectory) throws IOException {
        validateFile(file);

        // Generate unique filename
        String uniqueFilename = generateUniqueFilename(file.getOriginalFilename());

        // Determine target path
        Path targetPath = uploadPath.resolve(subdirectory).resolve(uniqueFilename);

        // Ensure parent directory exists
        Files.createDirectories(targetPath.getParent());

        // Copy file to target location
        Files.copy(file.getInputStream(), targetPath, StandardCopyOption.REPLACE_EXISTING);

        return targetPath.toString();
    }

    /**
     * Validate uploaded file.
     *
     * @param file File to validate
     * @throws IllegalArgumentException If file is invalid
     */
    public void validateFile(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("File is empty or null");
        }

        // Check file size
        if (file.getSize() > fileStorageConfig.getMaxSize()) {
            long maxSizeMB = fileStorageConfig.getMaxSize() / (1024 * 1024);
            throw new IllegalArgumentException(
                    "File size exceeds maximum allowed size of " + maxSizeMB + "MB"
            );
        }

        // Check file type
        String filename = file.getOriginalFilename();
        if (filename == null) {
            throw new IllegalArgumentException("Filename is null");
        }

        String extension = getFileExtension(filename);
        List<String> allowedTypes = Arrays.asList(
                fileStorageConfig.getAllowedTypes().split(",")
        );

        if (!allowedTypes.contains(extension.toLowerCase())) {
            throw new IllegalArgumentException(
                    "Invalid file type: " + extension +
                            ". Allowed types: " + fileStorageConfig.getAllowedTypes()
            );
        }

        // Validate content type
        String contentType = file.getContentType();
        if (contentType == null || !contentType.startsWith("image/")) {
            throw new IllegalArgumentException(
                    "Invalid content type: " + contentType + ". Must be an image file."
            );
        }
    }

    /**
     * Generate unique filename with timestamp.
     *
     * @param originalFilename Original filename from upload
     * @return Unique filename
     */
    public String generateUniqueFilename(String originalFilename) {
        String timestamp = LocalDateTime.now().format(
                DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss")
        );

        String extension = getFileExtension(originalFilename);
        String baseName = getBaseName(originalFilename);

        // Clean base name (remove special characters)
        baseName = baseName.replaceAll("[^a-zA-Z0-9_-]", "_");

        return timestamp + "_" + baseName + "." + extension;
    }

    /**
     * Delete file at specified path.
     *
     * @param filePath Path to file
     * @throws IOException If deletion fails
     */
    public void deleteFile(String filePath) throws IOException {
        Path path = Path.of(filePath);
        if (Files.exists(path)) {
            Files.delete(path);
        }
    }

    /**
     * Get file extension from filename.
     */
    private String getFileExtension(String filename) {
        int lastDotIndex = filename.lastIndexOf('.');
        if (lastDotIndex > 0) {
            return filename.substring(lastDotIndex + 1);
        }
        return "";
    }

    /**
     * Get base filename without extension.
     */
    private String getBaseName(String filename) {
        int lastDotIndex = filename.lastIndexOf('.');
        if (lastDotIndex > 0) {
            return filename.substring(0, lastDotIndex);
        }
        return filename;
    }
}
