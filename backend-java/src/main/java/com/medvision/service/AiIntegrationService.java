package com.medvision.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.springframework.core.io.InputStreamResource;
import org.springframework.core.io.Resource;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * AI 集成服务 - 作为 Java 后端与 Python AI 服务之间的代理层。
 * <p>
 * 负责将前端请求转发至 Python 侧的各个内部接口（OCR、ASR、文本分析、Chat、TTS），
 * 并统一处理请求构建、响应解析和异常兜底。
 * 所有请求均携带 X-Internal-Token 进行内部鉴权。
 */
@Service
public class AiIntegrationService {

    private static final Logger log = LoggerFactory.getLogger(AiIntegrationService.class);

    /** Spring 提供的 HTTP 客户端，用于向 Python AI 服务发送请求 */
    private final RestTemplate restTemplate;

    /** Python AI 服务的基础 URL，从 application.properties 中注入 */
    @Value("${ai.service.url}")
    private String aiServiceUrl;

    /** 内部服务间调用的鉴权 Token，从 application.properties 中注入 */
    @Value("${internal.token:}")
    private String internalToken;

    /**
     * 构造函数，通过依赖注入获取 RestTemplate 实例
     *
     * @param restTemplate Spring 管理的 HTTP 客户端
     */
    public AiIntegrationService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    /**
     * 调用 Python OCR 服务识别药品图片。
     * <p>
     * 将前端上传的图片文件以 multipart/form-data 形式转发至 Python OCR 接口，
     * 解析返回的 JSON 获取识别出的药品说明书文本和药品名称。
     *
     * @param file 前端上传的图片文件
     * @return 包含 "text"（识别文本）和 "name"（药品名称）的 Map
     * @throws IOException  文件读取异常
     * @throws RuntimeException OCR 服务不可用时抛出
     */
    public Map<String, String> callOcr(MultipartFile file) throws IOException {
        String url = aiServiceUrl + "/internal/ocr";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        headers.set("X-Internal-Token", internalToken);

        // 构建 multipart 请求体，保留原始文件名
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", new ByteArrayResource(file.getBytes()) {
            @Override
            public String getFilename() {
                return file.getOriginalFilename();
            }
        });

        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

        try {
            ResponseEntity<String> response = restTemplate.postForEntity(url, requestEntity, String.class);

            // 解析 JSON 响应：{"text": "...", "name": "...", "file_path": "..."}
            ObjectMapper mapper = new ObjectMapper();
            JsonNode root = mapper.readTree(response.getBody());

            Map<String, String> result = new HashMap<>();
            result.put("text", root.path("text").asText());
            result.put("name", root.path("name").asText("未知药品"));
            return result;
        } catch (Exception e) {
            log.error("OCR 服务调用失败", e);
            throw new RuntimeException("OCR Service Unavailable");
        }
    }

    /**
     * 调用 Python ASR 语音转写服务（代理前端语音请求，前端不再直连 Python）。
     * <p>
     * 将前端录制的语音文件转发至 Python Whisper ASR 接口，
     * 返回转写状态、纠错后文本及原始识别文本。
     *
     * @param file 前端上传的语音文件
     * @return 包含 "status"（转写状态）、"text"（纠错后文本）、"raw"（原始识别文本）的 Map
     * @throws IOException  文件读取异常
     * @throws RuntimeException ASR 服务不可用时抛出
     */
    public Map<String, String> callTranscribe(MultipartFile file) throws IOException {
        String url = aiServiceUrl + "/internal/transcribe";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        headers.set("X-Internal-Token", internalToken);

        // 构建 multipart 请求体，保留原始文件名
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", new ByteArrayResource(file.getBytes()) {
            @Override
            public String getFilename() {
                return file.getOriginalFilename();
            }
        });

        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

        try {
            ResponseEntity<String> response = restTemplate.postForEntity(url, requestEntity, String.class);
            ObjectMapper mapper = new ObjectMapper();
            JsonNode root = mapper.readTree(response.getBody());

            Map<String, String> result = new HashMap<>();
            result.put("status", root.path("status").asText(""));
            result.put("text", root.path("text").asText());
            result.put("raw", root.path("raw").asText(""));
            return result;
        } catch (Exception e) {
            log.error("语音转写服务调用失败", e);
            throw new RuntimeException("ASR Service Unavailable");
        }
    }

    /**
     * 调用 Python 文本分析服务（代理前端手动输入请求）。
     * <p>
     * 当用户通过文字而非语音输入药品相关信息时，将文本发送至 Python 侧进行分析，
     * 返回分析后的文本和识别出的药品名称。
     *
     * @param text 用户手动输入的文本内容
     * @return 包含 "text"（分析后文本）和 "name"（药品名称）的 Map
     * @throws RuntimeException 文本分析服务不可用时抛出
     */
    public Map<String, String> callAnalyzeText(String text) {
        String url = aiServiceUrl + "/internal/analyze_text";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("X-Internal-Token", internalToken);

        Map<String, Object> map = new HashMap<>();
        map.put("text", text);

        HttpEntity<Map<String, Object>> request = new HttpEntity<>(map, headers);

        try {
            ResponseEntity<String> response = restTemplate.postForEntity(url, request, String.class);
            ObjectMapper mapper = new ObjectMapper();
            JsonNode root = mapper.readTree(response.getBody());

            Map<String, String> result = new HashMap<>();
            result.put("text", root.path("text").asText());
            result.put("name", root.path("name").asText("未知药品"));
            return result;
        } catch (Exception e) {
            log.error("文本分析服务调用失败", e);
            throw new RuntimeException("Text Analysis Service Unavailable");
        }
    }

    /**
     * 调用 Python Chat 对话服务（支持 RAG 检索增强生成）。
     * <p>
     * 将用户问题和药品说明书上下文发送至 Python Chat 接口，
     * 由 Python 侧调用 LLM 生成回答并返回 RAG 引用来源。
     * 支持按药品 ID 持久化存储至 ChromaDB，并支持多语言和模型切换。
     *
     * @param context       药品说明书文本上下文
     * @param question      用户提出的问题
     * @param medicineId    药品 ID，用于 ChromaDB 按药品持久化向量存储
     * @param medicineName  药品名称，传递给 Python 用于邮件预警
     * @param language      回答语言（如 "zh"、"en"），支持多语言
     * @param model         聊天模型名称，用于切换不同的 LLM
     * @return 包含 "answer"（AI 回答）和 "citations"（RAG 引用来源列表）的 Map
     * @throws RuntimeException Chat 服务不可用时返回兜底回答而非抛出异常
     */
    public Map<String, Object> callChat(String context, String question, Long medicineId, String medicineName, String language, String model) {
        String url = aiServiceUrl + "/internal/chat";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("X-Internal-Token", internalToken);

        Map<String, Object> map = new HashMap<>();
        map.put("context", context);
        map.put("question", question);
        map.put("medicine_id", medicineId);      // 用于 ChromaDB 按药品持久化存储
        map.put("medicine_name", medicineName);   // 传递给 Python 用于邮件预警
        map.put("language", language);            // 多语言支持
        map.put("model", model);                  // 聊天模型切换

        HttpEntity<Map<String, Object>> request = new HttpEntity<>(map, headers);

        try {
            ResponseEntity<String> response = restTemplate.postForEntity(url, request, String.class);
            ObjectMapper mapper = new ObjectMapper();
            JsonNode root = mapper.readTree(response.getBody());

            Map<String, Object> result = new HashMap<>();
            result.put("answer", root.path("answer").asText());

            // 解析 RAG 引用来源（citations 为 JSON 数组）
            JsonNode citationsNode = root.path("citations");
            if (citationsNode.isArray()) {
                result.put("citations", mapper.convertValue(citationsNode, List.class));
            } else {
                result.put("citations", List.of());
            }

            return result;
        } catch (Exception e) {
            log.error("Chat 服务调用失败", e);
            // 服务不可用时返回兜底回答，避免前端崩溃
            Map<String, Object> fallback = new HashMap<>();
            fallback.put("answer", "AI服务暂时不可用，请稍后再试。");
            fallback.put("citations", List.of());
            return fallback;
        }
    }

    /**
     * 调用 Python TTS 文本转语音服务（代理前端请求）。
     * <p>
     * 使用原生 HttpURLConnection 而非 RestTemplate，以便更好地控制流式音频数据的读取。
     * 将文本通过 GET 请求发送至 Python TTS 接口，返回 audio/mpeg 格式的音频流。
     *
     * @param text 需要转换为语音的文本内容
     * @return 包含音频字节流的 ResponseEntity，Content-Type 为 audio/mpeg
     * @throws RuntimeException TTS 服务不可用或返回空内容时抛出
     */
    public ResponseEntity<Resource> callTts(String text) {
        try {
            // 对文本进行 URL 编码，拼接 TTS 请求地址
            String ttsUrl = aiServiceUrl + "/internal/tts?text=" + java.net.URLEncoder.encode(text, "UTF-8");
            log.info("TTS请求URL: {}", ttsUrl);

            // 使用原生 HttpURLConnection 发送 GET 请求，便于流式读取音频数据
            HttpURLConnection conn = (HttpURLConnection) new URL(ttsUrl).openConnection();
            conn.setRequestMethod("GET");
            conn.setRequestProperty("X-Internal-Token", internalToken);
            conn.setConnectTimeout(30000);  // 连接超时 30 秒
            conn.setReadTimeout(30000);     // 读取超时 30 秒

            int statusCode = conn.getResponseCode();
            int contentLength = conn.getContentLength();
            String contentType = conn.getContentType();
            log.info("TTS响应: status={}, contentLength={}, contentType={}", statusCode, contentLength, contentType);

            // 上游返回非 200 状态码时，读取错误流并抛出异常
            if (statusCode != 200) {
                String errBody = "";
                try (InputStream es = conn.getErrorStream()) {
                    if (es != null) errBody = new String(es.readAllBytes(), java.nio.charset.StandardCharsets.UTF_8);
                }
                log.error("TTS上游返回非200: {}, body={}", statusCode, errBody);
                conn.disconnect();
                throw new RuntimeException("TTS Upstream Error: " + statusCode);
            }

            // 从输入流中读取完整的音频字节数据
            byte[] audioBytes;
            try (InputStream is = conn.getInputStream()) {
                java.io.ByteArrayOutputStream bos = new java.io.ByteArrayOutputStream();
                byte[] buf = new byte[4096];
                int n;
                while ((n = is.read(buf)) != -1) {
                    bos.write(buf, 0, n);
                }
                audioBytes = bos.toByteArray();
            } finally {
                conn.disconnect();
            }

            log.info("TTS读取完成: {}bytes", audioBytes.length);

            // 防御性检查：音频数据为空时抛出异常
            if (audioBytes.length == 0) {
                log.error("TTS返回空内容, contentLength={}, contentType={}", contentLength, contentType);
                throw new RuntimeException("TTS Empty Response");
            }

            // 构建音频响应，设置 Content-Type 为 audio/mpeg
            HttpHeaders responseHeaders = new HttpHeaders();
            responseHeaders.setContentType(MediaType.parseMediaType("audio/mpeg"));
            responseHeaders.setContentLength(audioBytes.length);

            return new ResponseEntity<>(
                new InputStreamResource(new java.io.ByteArrayInputStream(audioBytes)),
                responseHeaders,
                HttpStatus.OK
            );
        } catch (RuntimeException e) {
            // RuntimeException 直接向上抛出（包含自定义的错误信息）
            throw e;
        } catch (Exception e) {
            log.error("TTS服务调用失败", e);
            throw new RuntimeException("TTS Service Unavailable");
        }
    }
}
