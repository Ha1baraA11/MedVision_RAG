package com.medvision.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

/**
 * 管理员实体 - 对应数据库 admin_users 表。
 * 存储管理员登录信息，密码使用 BCrypt 加密存储。
 */
@Entity
@Table(name = "admin_users")
public class AdminUser {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** 登录用户名，唯一约束 */
    @Column(nullable = false, unique = true, length = 50)
    private String username;

    /** BCrypt 加密后的密码 */
    @Column(nullable = false, length = 100)
    private String passwordHash;

    /** 显示名称 */
    @Column(length = 50)
    private String realName;

    /** 账号状态：1=启用，0=禁用 */
    @Column(nullable = false)
    private Integer status = 1;

    /** 连续登录失败次数 */
    @Column
    private Integer failedAttempts = 0;

    /** 锁定到期时间，null 表示未锁定 */
    private LocalDateTime lockTime;

    /** 最后成功登录时间 */
    private LocalDateTime lastLoginTime;

    /** 记录创建时间 */
    private LocalDateTime createTime;

    @PrePersist
    public void prePersist() {
        this.createTime = LocalDateTime.now(java.time.ZoneId.of("Asia/Shanghai"));
        if (this.status == null) this.status = 1;
        if (this.failedAttempts == null) this.failedAttempts = 0;
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }

    public String getPasswordHash() { return passwordHash; }
    public void setPasswordHash(String passwordHash) { this.passwordHash = passwordHash; }

    public String getRealName() { return realName; }
    public void setRealName(String realName) { this.realName = realName; }

    public Integer getStatus() { return status; }
    public void setStatus(Integer status) { this.status = status; }

    public Integer getFailedAttempts() { return failedAttempts; }
    public void setFailedAttempts(Integer failedAttempts) { this.failedAttempts = failedAttempts; }

    public LocalDateTime getLockTime() { return lockTime; }
    public void setLockTime(LocalDateTime lockTime) { this.lockTime = lockTime; }

    public LocalDateTime getLastLoginTime() { return lastLoginTime; }
    public void setLastLoginTime(LocalDateTime lastLoginTime) { this.lastLoginTime = lastLoginTime; }

    public LocalDateTime getCreateTime() { return createTime; }
    public void setCreateTime(LocalDateTime createTime) { this.createTime = createTime; }
}
