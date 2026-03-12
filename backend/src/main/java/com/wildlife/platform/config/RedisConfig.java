package com.wildlife.platform.config;

import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.time.Duration;
import java.util.Map;

@Configuration
@EnableCaching
public class RedisConfig {

    /**
     * Default cache config: JSON serialization, 5 minute TTL.
     * Individual caches can override the TTL via cacheConfigurations().
     */
    @Bean
    RedisCacheManager cacheManager(RedisConnectionFactory factory) {
        RedisCacheConfiguration defaults = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(5))
                .serializeKeysWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new StringRedisSerializer()))
                .serializeValuesWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new GenericJackson2JsonRedisSerializer()))
                .disableCachingNullValues();

        return RedisCacheManager.builder(factory)
                .cacheDefaults(defaults)
                .withInitialCacheConfigurations(Map.of(
                        // Species list rarely changes — cache for 10 minutes
                        "species",      defaults.entryTtl(Duration.ofMinutes(10)),
                        // Individual species lookups — cache for 10 minutes
                        "speciesById",  defaults.entryTtl(Duration.ofMinutes(10)),
                        "speciesByName", defaults.entryTtl(Duration.ofMinutes(10)),
                        // Prediction stats update with every new prediction — shorter TTL
                        "predictionStats", defaults.entryTtl(Duration.ofMinutes(1))
                ))
                .build();
    }
}
