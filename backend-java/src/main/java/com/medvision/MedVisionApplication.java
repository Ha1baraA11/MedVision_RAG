package com.medvision;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.web.client.RestTemplate;

/**
 * MedVision-RAG 应用程序启动类。
 * <p>
 * 基于 Spring Boot 的药品智能问答系统后端，
 * 负责整合 OCR、ASR、LLM Chat、TTS 等 AI 服务能力，
 * 为微信小程序前端提供统一的 RESTful API。
 */
@SpringBootApplication
public class MedVisionApplication {

    /**
     * 应用程序入口方法，启动 Spring Boot 容器
     *
     * @param args 命令行参数
     */
    public static void main(String[] args) {
        SpringApplication.run(MedVisionApplication.class, args);
    }

    /**
     * 注册 RestTemplate Bean，用于服务间 HTTP 调用。
     * AiIntegrationService 通过此 Bean 向 Python AI 服务发送请求。
     *
     * @return RestTemplate 实例
     */
    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}
