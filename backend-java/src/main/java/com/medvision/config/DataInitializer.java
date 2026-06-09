package com.medvision.config;

import com.medvision.entity.AdminUser;
import com.medvision.repository.AdminUserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

/**
 * 应用启动时初始化默认管理员账号。
 * 仅在 admin_users 表为空时插入，不影响已有数据。
 */
@Component
public class DataInitializer implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(DataInitializer.class);

    private final AdminUserRepository adminUserRepository;
    private final PasswordEncoder passwordEncoder;

    public DataInitializer(AdminUserRepository adminUserRepository, PasswordEncoder passwordEncoder) {
        this.adminUserRepository = adminUserRepository;
        this.passwordEncoder = passwordEncoder;
    }

    @Override
    public void run(String... args) {
        String defaultAdmin = System.getenv("ADMIN_USERNAME");
        String defaultPassword = System.getenv("ADMIN_PASSWORD");
        if (defaultAdmin == null || defaultAdmin.isEmpty()) defaultAdmin = "admin";
        if (defaultPassword == null || defaultPassword.isEmpty()) defaultPassword = "admin";

        if (adminUserRepository.existsByUsername(defaultAdmin)) {
            log.info("默认管理员账号已存在，跳过初始化");
            return;
        }

        AdminUser admin = new AdminUser();
        admin.setUsername(defaultAdmin);
        admin.setPasswordHash(passwordEncoder.encode(defaultPassword));
        admin.setRealName("管理员");
        admin.setStatus(1);
        admin.setFailedAttempts(0);

        adminUserRepository.save(admin);
        log.info("默认管理员账号已创建: username={}", defaultAdmin);
    }
}
