package com.medvision.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

/**
 * 聊天日志实体 - 用于 Admin Dashboard 实时监控
 * 记录每次语音问答的完整链路数据
 */
@Entity
@Table(name = "chat_logs")
public class ChatLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // 用户标识 (可选，用于多用户场景)
    private String userId;

    // 关联的药品 ID
    private Long medicineId;

    // 关联的药品名称 (冗余存储，方便查询)
    private String medicineName;

    // 用户本次问答所选模型
    private String chatModel;

    // 原始 ASR 识别结果 (Whisper 直接输出)
    @Column(columnDefinition = "TEXT")
    private String rawAsr;

    // LLM 纠错后的文本
    @Column(columnDefinition = "TEXT")
    private String correctedText;

    // AI 回复内容
    @Column(columnDefinition = "TEXT")
    private String response;

    // 响应状态 (SUCCESS / TIMEOUT / ERROR)
    private String responseStatus;

    // 处理延迟 (毫秒)
    private Integer latencyMs;

    // 是否触发风险关键词
    private Boolean isRisky;

    // 创建时间
    private LocalDateTime createTime;

    /**
     * JPA 实体持久化前的回调方法。
     * 自动设置创建时间为上海时区的当前时间，若未指定用户 ID 则默认为 "default_user"。
     */
    @PrePersist
    public void prePersist() {
        this.createTime = LocalDateTime.now(java.time.ZoneId.of("Asia/Shanghai"));
        if (this.userId == null) {
            this.userId = "default_user";
        }
    }

    // ==================== Getters and Setters ====================
    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getUserId() {
        return userId;
    }

    public void setUserId(String userId) {
        this.userId = userId;
    }

    public Long getMedicineId() {
        return medicineId;
    }

    public void setMedicineId(Long medicineId) {
        this.medicineId = medicineId;
    }

    public String getMedicineName() {
        return medicineName;
    }

    public void setMedicineName(String medicineName) {
        this.medicineName = medicineName;
    }

    public String getChatModel() {
        return chatModel;
    }

    public void setChatModel(String chatModel) {
        this.chatModel = chatModel;
    }

    public String getRawAsr() {
        return rawAsr;
    }

    public void setRawAsr(String rawAsr) {
        this.rawAsr = rawAsr;
    }

    public String getCorrectedText() {
        return correctedText;
    }

    public void setCorrectedText(String correctedText) {
        this.correctedText = correctedText;
    }

    public String getResponse() {
        return response;
    }

    public void setResponse(String response) {
        this.response = response;
    }

    public String getResponseStatus() {
        return responseStatus;
    }

    public void setResponseStatus(String responseStatus) {
        this.responseStatus = responseStatus;
    }

    public Integer getLatencyMs() {
        return latencyMs;
    }

    public void setLatencyMs(Integer latencyMs) {
        this.latencyMs = latencyMs;
    }

    public Boolean getIsRisky() {
        return isRisky;
    }

    public void setIsRisky(Boolean isRisky) {
        this.isRisky = isRisky;
    }

    public LocalDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(LocalDateTime createTime) {
        this.createTime = createTime;
    }
}
