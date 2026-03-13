package com.wildlife.platform.controller;

import org.apache.kafka.clients.admin.AdminClient;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.kafka.core.KafkaAdmin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class HealthController {

    private final RedisConnectionFactory redisConnectionFactory;
    private final KafkaAdmin kafkaAdmin;

    public HealthController(RedisConnectionFactory redisConnectionFactory, KafkaAdmin kafkaAdmin) {
        this.redisConnectionFactory = redisConnectionFactory;
        this.kafkaAdmin = kafkaAdmin;
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        Map<String, Object> result = new HashMap<>();
        result.put("status", "healthy");
        result.put("service", "Wildlife MLOps Platform");
        result.put("timestamp", Instant.now().toString());
        result.put("redis", checkRedis());
        result.put("kafka", checkKafka());
        return result;
    }

    private String checkRedis() {
        try {
            redisConnectionFactory.getConnection().ping();
            return "UP";
        } catch (Exception e) {
            return "DOWN";
        }
    }

    private String checkKafka() {
        try (AdminClient client = AdminClient.create(kafkaAdmin.getConfigurationProperties())) {
            client.listTopics().names().get();
            return "UP";
        } catch (Exception e) {
            return "DOWN";
        }
    }
}
