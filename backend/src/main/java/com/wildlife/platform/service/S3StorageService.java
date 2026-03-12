package com.wildlife.platform.service;

import com.wildlife.platform.config.S3Properties;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.*;

import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@Slf4j
@Service
@RequiredArgsConstructor
public class S3StorageService {

    private final S3Client s3Client;
    private final S3Properties s3Properties;

    /**
     * Ensure the S3 bucket exists on startup.
     * Works with MinIO locally and AWS S3 in production.
     */
    @PostConstruct
    void ensureBucketExists() {
        try {
            s3Client.headBucket(HeadBucketRequest.builder().bucket(s3Properties.getBucket()).build());
            log.info("S3 bucket '{}' already exists", s3Properties.getBucket());
        } catch (NoSuchBucketException e) {
            s3Client.createBucket(CreateBucketRequest.builder().bucket(s3Properties.getBucket()).build());
            log.info("Created S3 bucket '{}'", s3Properties.getBucket());
        } catch (Exception e) {
            log.warn("Could not verify S3 bucket '{}': {}", s3Properties.getBucket(), e.getMessage());
        }
    }

    /**
     * Upload a file to S3/MinIO under the given subfolder.
     *
     * @param file      The multipart file to upload
     * @param subfolder e.g. "predictions"
     * @return The public URL of the uploaded object
     */
    public String uploadFile(MultipartFile file, String subfolder) throws IOException {
        String key = subfolder + "/" + generateUniqueFilename(file.getOriginalFilename());

        s3Client.putObject(
                PutObjectRequest.builder()
                        .bucket(s3Properties.getBucket())
                        .key(key)
                        .contentType(file.getContentType())
                        .contentLength(file.getSize())
                        .build(),
                RequestBody.fromInputStream(file.getInputStream(), file.getSize())
        );

        String url = s3Properties.getEndpoint() + "/" + s3Properties.getBucket() + "/" + key;
        log.info("Uploaded file to S3: {}", url);
        return url;
    }

    /**
     * Delete an object from S3/MinIO by its key.
     */
    public void deleteFile(String key) {
        try {
            s3Client.deleteObject(DeleteObjectRequest.builder().bucket(s3Properties.getBucket()).key(key).build());
            log.info("Deleted S3 object: {}", key);
        } catch (Exception e) {
            log.warn("Failed to delete S3 object '{}': {}", key, e.getMessage());
        }
    }

    private String generateUniqueFilename(String originalFilename) {
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        if (originalFilename == null) return timestamp + ".jpg";
        int dot = originalFilename.lastIndexOf('.');
        String ext = dot > 0 ? originalFilename.substring(dot + 1) : "jpg";
        String base = dot > 0 ? originalFilename.substring(0, dot) : originalFilename;
        base = base.replaceAll("[^a-zA-Z0-9_-]", "_");
        return timestamp + "_" + base + "." + ext;
    }
}
