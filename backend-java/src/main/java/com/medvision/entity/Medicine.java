package com.medvision.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

/**
 * 药品实体 - 对应数据库 medicines 表。
 * <p>
 * 存储药品的基本信息，包括药品名称、说明书全文和药品图片 URL。
 * 作为 RAG 检索的知识库数据源，每条记录对应一种药品的完整信息。
 */
@Entity
@Table(name = "medicines")
public class Medicine {

    /** 药品记录主键，自增 ID */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** 药品名称 */
    private String name;

    /** 药品说明书全文内容，用于 RAG 检索的知识库文本 */
    @Column(columnDefinition = "TEXT")
    private String fullText;

    /** 药品图片的访问 URL */
    private String imageUrl;

    /** 记录创建时间 */
    private LocalDateTime createTime;

    /**
     * JPA 实体持久化前的回调方法。
     * 自动设置创建时间为上海时区的当前时间。
     */
    @PrePersist
    public void prePersist() {
        this.createTime = LocalDateTime.now(java.time.ZoneId.of("Asia/Shanghai"));
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getFullText() {
        return fullText;
    }

    public void setFullText(String fullText) {
        this.fullText = fullText;
    }

    public String getImageUrl() {
        return imageUrl;
    }

    public void setImageUrl(String imageUrl) {
        this.imageUrl = imageUrl;
    }

    public LocalDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(LocalDateTime createTime) {
        this.createTime = createTime;
    }
}
