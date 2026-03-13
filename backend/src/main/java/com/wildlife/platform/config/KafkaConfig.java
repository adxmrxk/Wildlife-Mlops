package com.wildlife.platform.config;

import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

@Configuration
public class KafkaConfig {

    @Bean
    public NewTopic predictionsTopic() {
        return TopicBuilder.name("wildlife.predictions")
                .partitions(3)
                .replicas(1)
                .build();
    }

    @Bean
    public NewTopic feedbackTopic() {
        return TopicBuilder.name("wildlife.feedback")
                .partitions(3)
                .replicas(1)
                .build();
    }

    @Bean
    public NewTopic retrainTopic() {
        return TopicBuilder.name("wildlife.retrain")
                .partitions(1)
                .replicas(1)
                .build();
    }
}
