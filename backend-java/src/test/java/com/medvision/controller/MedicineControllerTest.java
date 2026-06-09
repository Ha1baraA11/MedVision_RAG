package com.medvision.controller;

import com.medvision.entity.ChatLog;
import com.medvision.entity.Medicine;
import com.medvision.repository.ChatLogRepository;
import com.medvision.repository.MedicineRepository;
import com.medvision.service.AiIntegrationService;

import com.fasterxml.jackson.databind.ObjectMapper;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.mock.web.MockMultipartFile;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * MedicineController.chat() 单元测试
 * ====================================
 * 使用 Standalone MockMvc (无需启动 Spring 容器)，
 * 所有依赖通过 Mockito @Mock 注入。
 * 不连接真实数据库，不调用真实 Python AI 服务。
 *
 * 运行方式: cd backend-java && mvn test
 */
@ExtendWith(MockitoExtension.class)
class MedicineControllerTest {

    private MockMvc mockMvc;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Mock
    private MedicineRepository medicineRepository;

    @Mock
    private ChatLogRepository chatLogRepository;

    @Mock
    private AiIntegrationService aiService;

    @BeforeEach
    void setUp() {
        MedicineController controller = new MedicineController(
                medicineRepository, chatLogRepository, aiService);
        mockMvc = MockMvcBuilders.standaloneSetup(controller).build();
    }

    private Map<String, Object> chatResult(String answer) {
        Map<String, Object> result = new HashMap<>();
        result.put("answer", answer);
        result.put("citations", List.of());
        return result;
    }

    // ============================================================
    // 1. 标准模式：根据 medicineId 查到药品，正常返回
    // ============================================================
    @Test
    @DisplayName("标准模式 - 正常问答返回200且包含answer")
    void chat_standardMode_returnsAnswer() throws Exception {
        // 准备: 数据库中存在 ID=1 的药品
        Medicine medicine = new Medicine();
        medicine.setId(1L);
        medicine.setName("阿莫西林胶囊");
        medicine.setFullText("阿莫西林胶囊说明书全文...");
        when(medicineRepository.findById(1L)).thenReturn(Optional.of(medicine));

        // AI 服务正常返回
        when(aiService.callChat(anyString(), anyString(), anyLong(), anyString(), anyString(), eq("deepseek-v4-pro")))
                .thenReturn(chatResult("每次服用一粒，每日三次。"));

        // ChatLog 保存
        ArgumentCaptor<ChatLog> captor = ArgumentCaptor.forClass(ChatLog.class);
        when(chatLogRepository.save(captor.capture())).thenAnswer(inv -> inv.getArgument(0));

        // 构造请求
        Map<String, Object> payload = new HashMap<>();
        payload.put("medicineId", 1);
        payload.put("question", "这个药怎么吃");
        payload.put("model", "deepseek-v4-pro");

        // 执行 & 验证
        mockMvc.perform(post("/api/medicine/chat")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(payload)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.answer").value("每次服用一粒，每日三次。"));

        verify(aiService).callChat(
                eq("阿莫西林胶囊说明书全文..."),
                eq("这个药怎么吃"),
                eq(1L),
                eq("阿莫西林胶囊"),
                eq("zh"),
                eq("deepseek-v4-pro"));
        assertEquals("DeepSeek V4 Pro", captor.getValue().getChatModel());
    }

    // ============================================================
    // 2. 手动输入模式：传入 context，不查数据库
    // ============================================================
    @Test
    @DisplayName("手动模式 - 携带context时不查数据库也能返回")
    void chat_manualMode_skipsDatabase() throws Exception {
        // AI 服务正常返回
        when(aiService.callChat(anyString(), anyString(), anyLong(), anyString(), anyString(), eq("deepseek-v4-flash")))
                .thenReturn(chatResult("建议饭后半小时服用。"));

        when(chatLogRepository.save(any(ChatLog.class))).thenAnswer(inv -> inv.getArgument(0));

        // 构造请求 (携带 context，模拟手动输入模式)
        Map<String, Object> payload = new HashMap<>();
        payload.put("medicineId", 999);
        payload.put("question", "饭前还是饭后吃");
        payload.put("context", "阿莫西林胶囊，饭后服用...");
        payload.put("medicineName", "手动输入药品");
        payload.put("model", "deepseek-v4-flash");

        mockMvc.perform(post("/api/medicine/chat")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(payload)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.answer").value("建议饭后半小时服用。"));

        // 验证: 没有查数据库
        verify(medicineRepository, never()).findById(anyLong());
        verify(aiService).callChat(
                eq("阿莫西林胶囊，饭后服用..."),
                eq("饭前还是饭后吃"),
                eq(999L),
                eq("手动输入药品"),
                eq("zh"),
                eq("deepseek-v4-flash"));
    }

    @Test
    @DisplayName("兼容旧请求 - 未传model时仍可正常问答")
    void chat_withoutModel_remainsCompatible() throws Exception {
        Medicine medicine = new Medicine();
        medicine.setId(6L);
        medicine.setName("维生素B");
        medicine.setFullText("维生素B说明书全文...");
        when(medicineRepository.findById(6L)).thenReturn(Optional.of(medicine));

        when(aiService.callChat(anyString(), anyString(), anyLong(), anyString(), anyString(), nullable(String.class)))
                .thenReturn(chatResult("建议按说明服用。"));

        when(chatLogRepository.save(any(ChatLog.class))).thenAnswer(inv -> inv.getArgument(0));

        Map<String, Object> payload = new HashMap<>();
        payload.put("medicineId", 6);
        payload.put("question", "怎么吃");

        mockMvc.perform(post("/api/medicine/chat")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(payload)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.answer").value("建议按说明服用。"));

        verify(aiService).callChat(
                eq("维生素B说明书全文..."),
                eq("怎么吃"),
                eq(6L),
                eq("维生素B"),
                eq("zh"),
                isNull());

        ArgumentCaptor<ChatLog> captor = ArgumentCaptor.forClass(ChatLog.class);
        verify(chatLogRepository).save(captor.capture());
        assertEquals("DeepSeek V4 Flash", captor.getValue().getChatModel());
    }

    // ============================================================
    // 3. AI 服务异常：接口仍应返回 200 + 友好提示
    // ============================================================
    @Test
    @DisplayName("AI服务异常 - 返回200且answer为友好提示")
    void chat_aiServiceError_returnsFallbackMessage() throws Exception {
        Medicine medicine = new Medicine();
        medicine.setId(2L);
        medicine.setName("布洛芬");
        medicine.setFullText("布洛芬缓释片说明书...");
        when(medicineRepository.findById(2L)).thenReturn(Optional.of(medicine));

        // AI 服务抛出异常
        when(aiService.callChat(anyString(), anyString(), anyLong(), anyString(), anyString(), nullable(String.class)))
                .thenThrow(new RuntimeException("Python 服务超时"));

        when(chatLogRepository.save(any(ChatLog.class))).thenAnswer(inv -> inv.getArgument(0));

        Map<String, Object> payload = new HashMap<>();
        payload.put("medicineId", 2);
        payload.put("question", "一次吃几粒");

        mockMvc.perform(post("/api/medicine/chat")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(payload)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.answer").value("AI服务暂时不可用，请稍后再试。"));
    }

    // ============================================================
    // 4. 聊天日志保存验证
    // ============================================================
    @Test
    @DisplayName("聊天日志 - 验证save()被调用且字段正确")
    void chat_savesLog_withCorrectFields() throws Exception {
        Medicine medicine = new Medicine();
        medicine.setId(3L);
        medicine.setName("头孢克肟");
        medicine.setFullText("头孢克肟分散片说明书...");
        when(medicineRepository.findById(3L)).thenReturn(Optional.of(medicine));

        when(aiService.callChat(anyString(), anyString(), anyLong(), anyString(), anyString(), nullable(String.class)))
                .thenReturn(chatResult("建议按照体重计算用量。"));

        ArgumentCaptor<ChatLog> captor = ArgumentCaptor.forClass(ChatLog.class);
        when(chatLogRepository.save(captor.capture())).thenAnswer(inv -> inv.getArgument(0));

        Map<String, Object> payload = new HashMap<>();
        payload.put("medicineId", 3);
        payload.put("question", "儿童怎么吃");

        mockMvc.perform(post("/api/medicine/chat")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(payload)))
                .andExpect(status().isOk());

        // 验证: save() 被调用了一次
        verify(chatLogRepository, times(1)).save(any(ChatLog.class));

        // 验证: 保存的日志字段正确
        ChatLog savedLog = captor.getValue();
        assertEquals(3L, savedLog.getMedicineId());
        assertEquals("头孢克肟", savedLog.getMedicineName());
        assertEquals("DeepSeek V4 Flash", savedLog.getChatModel());
        assertEquals("儿童怎么吃", savedLog.getCorrectedText());
        assertEquals("建议按照体重计算用量。", savedLog.getResponse());
        assertEquals("SUCCESS", savedLog.getResponseStatus());
    }

    // ============================================================
    // 5. 风险标记验证：answer 含风险词
    // ============================================================
    @Test
    @DisplayName("风险标记 - question含风险词时isRisky为true")
    void chat_riskyAnswer_setsIsRiskyTrue() throws Exception {
        Medicine medicine = new Medicine();
        medicine.setId(4L);
        medicine.setName("氯雷他定片");
        medicine.setFullText("氯雷他定片说明书...");
        when(medicineRepository.findById(4L)).thenReturn(Optional.of(medicine));

        // AI 回复内容不影响风险标记，风险词来自用户问题
        when(aiService.callChat(anyString(), anyString(), anyLong(), anyString(), anyString(), nullable(String.class)))
                .thenReturn(chatResult("青霉素过敏者禁用此药物，使用前请告知医生。"));

        ArgumentCaptor<ChatLog> captor = ArgumentCaptor.forClass(ChatLog.class);
        when(chatLogRepository.save(captor.capture())).thenAnswer(inv -> inv.getArgument(0));

        Map<String, Object> payload = new HashMap<>();
        payload.put("medicineId", 4);
        payload.put("question", "过敏体质可以吃吗");

        mockMvc.perform(post("/api/medicine/chat")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(payload)))
                .andExpect(status().isOk());

        ChatLog savedLog = captor.getValue();
        assertTrue(savedLog.getIsRisky(), "question 含'过敏'，isRisky 应为 true");
    }

    // ============================================================
    // 6. 风险标记验证：answer 不含风险词
    // ============================================================
    @Test
    @DisplayName("风险标记 - answer不含风险词时isRisky为false")
    void chat_safeAnswer_setsIsRiskyFalse() throws Exception {
        Medicine medicine = new Medicine();
        medicine.setId(5L);
        medicine.setName("维生素C");
        medicine.setFullText("维生素C片说明书...");
        when(medicineRepository.findById(5L)).thenReturn(Optional.of(medicine));

        // AI 回复中不包含风险关键词
        when(aiService.callChat(anyString(), anyString(), anyLong(), anyString(), anyString(), nullable(String.class)))
                .thenReturn(chatResult("每日一次，每次一粒，温水送服即可。"));

        ArgumentCaptor<ChatLog> captor = ArgumentCaptor.forClass(ChatLog.class);
        when(chatLogRepository.save(captor.capture())).thenAnswer(inv -> inv.getArgument(0));

        Map<String, Object> payload = new HashMap<>();
        payload.put("medicineId", 5);
        payload.put("question", "怎么吃");

        mockMvc.perform(post("/api/medicine/chat")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(payload)))
                .andExpect(status().isOk());

        ChatLog savedLog = captor.getValue();
        assertFalse(savedLog.getIsRisky(), "answer 无风险词，isRisky 应为 false");
    }

    @Test
    @DisplayName("语音转写代理 - 透传status、text和raw")
    void transcribe_proxy_returnsStatusTextAndRaw() throws Exception {
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "voice.webm",
                "audio/webm",
                "fake audio".getBytes()
        );

        Map<String, String> aiResult = new HashMap<>();
        aiResult.put("status", "hallucination");
        aiResult.put("text", "");
        aiResult.put("raw", "字幕组内容");
        when(aiService.callTranscribe(any())).thenReturn(aiResult);

        mockMvc.perform(multipart("/api/medicine/transcribe").file(file))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("hallucination"))
                .andExpect(jsonPath("$.text").value(""))
                .andExpect(jsonPath("$.raw").value("字幕组内容"));
    }
}
