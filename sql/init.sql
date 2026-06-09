-- ===========================================
--  MedVision-RAG 数据库初始化脚本
--  用法: mysql -u root -p < sql/init.sql
--  或在 MySQL 命令行中执行: SOURCE /path/to/init.sql
-- ===========================================

-- 创建数据库（如已存在则跳过）
CREATE DATABASE IF NOT EXISTS medvision
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE medvision;

-- -------------------------------------------
--  药品信息表
--  存储药品基本数据，OCR 识别后自动入库
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS medicines (
    id          BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(255) DEFAULT NULL COMMENT '药品名称',
    full_text   TEXT         DEFAULT NULL COMMENT '药品说明书全文（RAG 知识源）',
    image_url   VARCHAR(500) DEFAULT NULL COMMENT '药品图片访问 URL',
    create_time DATETIME     DEFAULT NULL COMMENT '入库时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='药品信息表';

-- -------------------------------------------
--  聊天日志表
--  记录每次语音问答的完整链路数据
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS chat_logs (
    id              BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id         VARCHAR(50)  DEFAULT 'default_user' COMMENT '用户标识',
    medicine_id     BIGINT       DEFAULT NULL COMMENT '关联药品 ID',
    medicine_name   VARCHAR(255) DEFAULT NULL COMMENT '关联药品名称（冗余）',
    chat_model      VARCHAR(50)  DEFAULT NULL COMMENT '本次问答使用的模型',
    raw_asr         TEXT         DEFAULT NULL COMMENT 'ASR 原始识别文本',
    corrected_text  TEXT         DEFAULT NULL COMMENT 'LLM 纠错后文本',
    response        TEXT         DEFAULT NULL COMMENT 'AI 回复内容',
    response_status VARCHAR(20)  DEFAULT NULL COMMENT '响应状态: SUCCESS / TIMEOUT / ERROR',
    latency_ms      INT          DEFAULT NULL COMMENT '处理延迟（毫秒）',
    is_risky        TINYINT(1)   DEFAULT 0    COMMENT '是否触发风险关键词',
    create_time     DATETIME     DEFAULT NULL COMMENT '记录时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天日志表';

-- -------------------------------------------
--  管理员账号表
--  默认账号由 DataInitializer 自动创建
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS admin_users (
    id              BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(50)  NOT NULL COMMENT '登录用户名',
    password_hash   VARCHAR(100) NOT NULL COMMENT 'BCrypt 加密密码',
    real_name       VARCHAR(50)  DEFAULT NULL COMMENT '显示名称',
    status          INT          NOT NULL DEFAULT 1 COMMENT '状态: 1=启用, 0=禁用',
    failed_attempts INT          DEFAULT 0  COMMENT '连续登录失败次数',
    lock_time       DATETIME     DEFAULT NULL COMMENT '锁定到期时间',
    last_login_time DATETIME     DEFAULT NULL COMMENT '最后登录时间',
    create_time     DATETIME     DEFAULT NULL COMMENT '创建时间',
    UNIQUE KEY uk_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='管理员账号表';
