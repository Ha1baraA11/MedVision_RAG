package com.medvision.controller;

// 实体类：药品和聊天日志的数据模型
import com.medvision.entity.ChatLog;
import com.medvision.entity.Medicine;
// 数据访问层：操作 MySQL 数据库的接口
import com.medvision.repository.ChatLogRepository;
import com.medvision.repository.MedicineRepository;
// 服务层：负责调用 Python AI 服务的代理类
import com.medvision.service.AiIntegrationService;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import java.io.IOException;
import java.util.Arrays;
import java.util.Map;
import java.util.List;
import java.util.HashMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * 药品问诊控制器
 * ================
 * 所有 HTTP 接口的入口，前端（Web / 小程序）的所有请求都打到这里。
 * 职责：接收请求 → 调用 AI 服务 → 保存日志 → 返回结果。
 *
 * 注意：本控制器不直接调用 Python，而是通过 AiIntegrationService 代理转发，
 * 实现"前端 → Java(8080) → Python(8001)"的统一网关架构。
 */
@RestController
@RequestMapping("/api/medicine")
@CrossOrigin(origins = {"http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:5173", "http://localhost:8502", "http://127.0.0.1:8502"}) // 跨域白名单：只允许指定来源访问
public class MedicineController {

    // 日志记录器，用于在控制台输出调试信息
    private static final Logger log = LoggerFactory.getLogger(MedicineController.class);

    // 风险关键词列表：用户提问中如果包含这些词，会被标记为"风险对话"
    // 同时会触发邮件预警通知（由 Python 端的 email.py 发送）
    private static final List<String> RISK_KEYWORDS = Arrays.asList(
            "副作用", "过敏", "禁忌", "禁用", "不良反应", "慎用", "忌用");

    // 三个核心依赖，通过构造函数注入（Spring 自动装配）
    private final MedicineRepository medicineRepository;   // 药品表的数据库操作
    private final ChatLogRepository chatLogRepository;     // 聊天日志表的数据库操作
    private final AiIntegrationService aiService;          // 调用 Python AI 服务的代理

    // 默认聊天模型标签（用于日志记录，区分用户选了哪个模型）
    private static final String DEFAULT_CHAT_MODEL_LABEL = "DeepSeek V4 Flash";

    /**
     * 构造函数：Spring 自动注入三个依赖
     * 这是依赖注入（DI）的标准写法，不用手动 new
     */
    public MedicineController(
            MedicineRepository medicineRepository,
            ChatLogRepository chatLogRepository,
            AiIntegrationService aiService) {
        this.medicineRepository = medicineRepository;
        this.chatLogRepository = chatLogRepository;
        this.aiService = aiService;
    }

    /**
     * 将前端传的模型标识转换为可读的模型名称（用于日志记录）
     * 例如: "deepseek-v4-pro" → "DeepSeek V4 Pro"
     */
    private String resolveChatModelLabel(String model) {
        if ("deepseek-v4-pro".equalsIgnoreCase(String.valueOf(model))) {
            return "DeepSeek V4 Pro";
        }
        return DEFAULT_CHAT_MODEL_LABEL;
    }

    // ========================================================
    // 接口 1: 图片上传 + OCR 识别 + 存入数据库
    // 前端拍照/选文件后调用此接口，返回识别出的药品信息
    // ========================================================
    @PostMapping("/upload")
    public ResponseEntity<Medicine> upload(@RequestParam("file") MultipartFile file) throws IOException {
        log.info("收到文件: {}", file.getOriginalFilename());

        // 第一步：把图片传给 Python OCR 服务，返回 {text=识别文本, name=药品名称}
        Map<String, String> ocrResult = aiService.callOcr(file);

        // 第二步：从返回结果中取出文本和药名
        String ocrText = ocrResult.getOrDefault("text", "");
        String medicineName = ocrResult.getOrDefault("name", "未知药品");

        // 第三步：构造药品实体，保存到 MySQL 的 medicines 表
        Medicine medicine = new Medicine();
        medicine.setName(medicineName);           // 药品名称
        medicine.setFullText(ocrText);            // 说明书全文（OCR 识别结果）
        medicine.setImageUrl("uploads/" + file.getOriginalFilename());  // 图片存储路径

        Medicine saved = medicineRepository.save(medicine);  // JPA 自动执行 INSERT 语句
        return ResponseEntity.ok(saved);  // 返回 200 + 药品信息（含自动生成的 id）
    }

    // ========================================================
    // 接口 1.1: 健康检查
    // 前端（小程序）启动时用此接口探测后端是否在线
    // 返回 "OK" 表示服务正常
    // ========================================================
    @GetMapping("/health")
    public ResponseEntity<String> healthCheck() {
        return ResponseEntity.ok("OK");
    }

    // ========================================================
    // 接口 1.2: 语音合成代理（TTS）
    // 接收文本，转发给 Python Edge TTS 服务，返回音频二进制流
    // 小程序用此接口播放 AI 回复的语音
    // ========================================================
    @GetMapping("/tts")
    public ResponseEntity<?> tts(@RequestParam("text") String text) {
        log.info("TTS 代理: 文本长度={}", text.length());
        return aiService.callTts(text);  // 直接透传 Python 返回的音频流
    }

    // ========================================================
    // 接口 1.5: 语音转写代理（ASR）
    // 接收录音文件，转发给 Python Whisper 服务，返回识别出的文字
    // 前端不再直连 Python，统一走 Java 网关
    // ========================================================
    @PostMapping("/transcribe")
    public ResponseEntity<Map<String, String>> transcribe(@RequestParam("file") MultipartFile file) throws IOException {
        log.info("语音转写代理: {}", file.getOriginalFilename());
        Map<String, String> result = aiService.callTranscribe(file);
        return ResponseEntity.ok(result);  // 返回 {status, text, raw}
    }

    // ========================================================
    // 接口 1.6: 手动文本分析代理
    // 前端"手动输入说明书"模式使用，文本发给 Python 分析后返回药名
    // ========================================================
    @PostMapping("/analyze_text")
    public ResponseEntity<Map<String, String>> analyzeText(@RequestBody Map<String, String> payload) {
        String text = payload.getOrDefault("text", "");
        log.info("文本分析代理: {} 字符", text.length());
        Map<String, String> result = aiService.callAnalyzeText(text);
        return ResponseEntity.ok(result);  // 返回 {text, name}
    }

    // ========================================================
    // 接口 2: 问答（核心接口）
    // 用户提问 → 查药品上下文 → 调 Python RAG → 保存聊天日志 → 返回回答
    // 这是最复杂的接口，串联了数据库读写、AI 调用、风险检测、日志记录
    // ========================================================
    @PostMapping("/chat")
    public ResponseEntity<Map<String, Object>> chat(@RequestBody Map<String, Object> payload) {
        // 记录请求开始时间，用于计算延迟
        long startTime = System.currentTimeMillis();

        // ---------- 解析前端传来的参数 ----------
        Long medicineId = ((Number) payload.get("medicineId")).longValue();  // 药品 ID
        String question = (String) payload.get("question");                 // 用户问题
        String rawAsr = (String) payload.getOrDefault("rawAsr", question);  // 原始 ASR 文本（用于对比纠错效果）
        String language = (String) payload.getOrDefault("language", "zh");  // 语言：zh 中文 / en 英文
        String model = (String) payload.getOrDefault("model", null);        // 用户选择的模型（Flash/Pro）
        String chatModelLabel = resolveChatModelLabel(model);               // 转成可读名称用于日志
        log.info("聊天请求模型: raw={}, resolved={}", model, chatModelLabel);
        // 手动输入模式下，前端直接传入说明书上下文，无需查库
        String directContext = (String) payload.getOrDefault("context", null);

        String context;       // 说明书上下文（给 RAG 用）
        String medicineName;  // 药品名称

        if (directContext != null && !directContext.isEmpty()) {
            // 手动输入模式：前端粘贴了说明书文本，直接用，不查数据库
            context = directContext;
            medicineName = (String) payload.getOrDefault("medicineName", "手动输入");
            log.info("聊天（手动模式）: medicineId={}, 上下文={}字符", medicineId, context.length());
        } else {
            // 标准模式：根据 medicineId 从 MySQL 查出药品的说明书全文
            Medicine medicine = medicineRepository.findById(medicineId)
                    .orElseThrow(() -> new RuntimeException("Medicine not found"));
            context = medicine.getFullText();   // 说明书全文作为 RAG 上下文
            medicineName = medicine.getName();  // 药品名称
        }

        // ---------- 调用 Python RAG 服务生成回答 ----------
        String answer;
        List<?> citations = List.of();  // RAG 引用来源（从向量库检索到的文本块）
        String status;
        try {
            // 调用 Python 的 /internal/chat 接口
            // 传递: 上下文、问题、药品ID（用于 ChromaDB 持久化）、药名（用于邮件预警）、语言、模型
            Map<String, Object> chatResult = aiService.callChat(context, question, medicineId, medicineName, language, model);
            answer = (String) chatResult.get("answer");                              // AI 回答
            citations = (List<?>) chatResult.getOrDefault("citations", List.of());   // 引用来源
            status = "SUCCESS";
        } catch (Exception e) {
            log.error("AI 服务调用失败", e);
            answer = "AI服务暂时不可用，请稍后再试。";
            status = "ERROR";
        }

        // 计算本次请求的总延迟（毫秒）
        long latency = System.currentTimeMillis() - startTime;

        // ---------- 风险关键词检测 ----------
        // 检查用户提问（不是 AI 回答）是否包含风险关键词
        // 包含的话标记为风险对话，管理后台会高亮显示
        boolean isRisky = RISK_KEYWORDS.stream().anyMatch(question::contains);

        // ---------- 保存聊天日志到 MySQL ----------
        // 记录完整的问答链路数据，供管理后台监控和分析
        try {
            ChatLog chatLog = new ChatLog();
            chatLog.setMedicineId(medicineId);        // 关联药品 ID
            chatLog.setMedicineName(medicineName);    // 药品名称（冗余存储，方便查询）
            chatLog.setChatModel(chatModelLabel);     // 使用的模型（Flash/Pro）
            chatLog.setRawAsr(rawAsr);                // 原始语音识别文本
            chatLog.setCorrectedText(question);       // 纠错后的问题（实际发送给 AI 的）
            chatLog.setResponse(answer);              // AI 回答内容
            chatLog.setResponseStatus(status);        // 响应状态（SUCCESS/ERROR）
            chatLog.setLatencyMs((int) latency);      // 处理延迟（毫秒）
            chatLog.setIsRisky(isRisky);              // 是否触发风险关键词
            chatLogRepository.save(chatLog);          // JPA 自动执行 INSERT 语句
            log.info("聊天日志已保存: 药品={}, 风险={}", medicineName, isRisky);
        } catch (Exception e) {
            // 日志保存失败不影响主流程，只记录警告
            log.warn("聊天日志保存失败（非关键错误）: {}", e.getMessage());
        }

        // ---------- 构造返回给前端的响应 ----------
        Map<String, Object> response = new HashMap<>();
        response.put("answer", answer);          // AI 回答文本
        response.put("citations", citations);    // RAG 引用来源
        return ResponseEntity.ok(response);
    }

    // ========================================================
    // 接口 3: 药品模糊搜索
    // Python 意图识别模块（intent.py）调用，搜索历史库存中的药品
    // 支持分页，防止结果集过大导致 OOM
    // ========================================================
    @GetMapping("/search")
    public ResponseEntity<Page<Medicine>> search(
            @RequestParam("name") String name,
            @RequestParam(value = "page", defaultValue = "0") int page,
            @RequestParam(value = "size", defaultValue = "10") int size) {
        log.info("搜索药品: 关键词={}, page={}, size={}", name, page, size);
        // JPA 根据方法名自动生成 SQL: SELECT * FROM medicines WHERE name LIKE '%关键词%' LIMIT ...
        Page<Medicine> results = medicineRepository.findByNameContaining(name, PageRequest.of(page, size));
        return ResponseEntity.ok(results);
    }

    // ========================================================
    // 管理后台 API（Admin Dashboard）
    // 以下接口供 Streamlit 管理后台调用，展示监控数据
    // 通过 AdminIpWhitelistFilter 做 IP 白名单限制
    // ========================================================

    /**
     * 接口 4: 获取最近聊天记录
     * 管理后台"实时监控"页面使用，按时间倒序分页返回
     */
    @GetMapping("/chat-logs")
    public ResponseEntity<Page<ChatLog>> getChatLogs(
            @RequestParam(value = "page", defaultValue = "0") int page,
            @RequestParam(value = "size", defaultValue = "100") int size) {
        Page<ChatLog> logs = chatLogRepository.findByOrderByCreateTimeDesc(PageRequest.of(page, size));
        return ResponseEntity.ok(logs);
    }

    /**
     * 接口 5: 获取风险对话列表
     * 管理后台"风险预警"页面使用，只返回 is_risky=true 的记录
     */
    @GetMapping("/chat-logs/risky")
    public ResponseEntity<Page<ChatLog>> getRiskyChatLogs(
            @RequestParam(value = "page", defaultValue = "0") int page,
            @RequestParam(value = "size", defaultValue = "100") int size) {
        Page<ChatLog> logs = chatLogRepository.findByIsRiskyTrueOrderByCreateTimeDesc(PageRequest.of(page, size));
        return ResponseEntity.ok(logs);
    }

    /**
     * 接口 6: 获取药品查询热度排行
     * 管理后台"热度分析"页面使用，统计每个药品被问了多少次，取 Top 10
     * 底层是 JPQL: SELECT medicineName, COUNT(*) FROM ChatLog GROUP BY medicineName
     */
    @GetMapping("/analytics/top-medicines")
    public ResponseEntity<List<Map<String, Object>>> getTopMedicines() {
        List<Object[]> results = chatLogRepository.countByMedicineName();
        // 把 Object[] 转成 {name, count} 的 Map 格式，方便前端直接用
        List<Map<String, Object>> formatted = results.stream()
                .limit(10)  // 只取前 10 名
                .map(row -> {
                    Map<String, Object> map = new HashMap<>();
                    map.put("name", row[0]);   // 药品名称
                    map.put("count", row[1]);  // 查询次数
                    return map;
                })
                .toList();
        return ResponseEntity.ok(formatted);
    }
}
