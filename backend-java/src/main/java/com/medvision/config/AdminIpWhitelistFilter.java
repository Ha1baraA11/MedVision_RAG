package com.medvision.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import org.springframework.lang.NonNull;

import java.io.IOException;
import java.util.Arrays;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 管理接口 IP 白名单过滤器
 * 
 * 仅拦截 Admin Dashboard 使用的管理接口，普通业务接口不受影响。
 * 通过 application.properties 中的 admin.security.ip-whitelist 配置允许访问的 IP。
 * 支持从 X-Forwarded-For 头获取反向代理后的真实 IP。
 */
@Component
@Order(1)
@ConditionalOnProperty(name = "admin.security.enabled", havingValue = "true", matchIfMissing = false)
public class AdminIpWhitelistFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(AdminIpWhitelistFilter.class);

    /** 需要保护的管理接口路径前缀 */
    private static final List<String> ADMIN_PATHS = List.of(
            "/api/medicine/chat-logs",
            "/api/medicine/analytics"
    );

    private final Set<String> allowedIps;

    public AdminIpWhitelistFilter(
            @Value("${admin.security.ip-whitelist:127.0.0.1,::1}") String ipWhitelist) {
        this.allowedIps = Arrays.stream(ipWhitelist.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .collect(Collectors.toSet());
        log.info("Admin IP 白名单已加载，共 {} 个地址", allowedIps.size());
    }

    @Override
    protected void doFilterInternal(@NonNull HttpServletRequest request,
                                    @NonNull HttpServletResponse response,
                                    @NonNull FilterChain filterChain) throws ServletException, IOException {

        String uri = request.getRequestURI();

        // 仅拦截管理接口
        boolean isAdminPath = ADMIN_PATHS.stream().anyMatch(uri::startsWith);
        if (!isAdminPath) {
            filterChain.doFilter(request, response);
            return;
        }

        // 解析客户端真实 IP（优先从反向代理头获取）
        String clientIp = resolveClientIp(request);

        if (allowedIps.contains(clientIp)) {
            filterChain.doFilter(request, response);
        } else {
            log.warn("Admin API 访问被拦截: IP={}, URI={}", clientIp, uri);
            response.setStatus(HttpServletResponse.SC_FORBIDDEN);
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write("{\"code\":403,\"message\":\"Forbidden: admin API is restricted\"}");
        }
    }

    /**
     * 解析客户端真实 IP。
     * 优先从 X-Forwarded-For 取第一个 IP（反向代理场景），
     * 否则回退到 request.getRemoteAddr()。
     */
    private String resolveClientIp(HttpServletRequest request) {
        String xff = request.getHeader("X-Forwarded-For");
        if (xff != null && !xff.isBlank()) {
            // X-Forwarded-For 格式: client, proxy1, proxy2
            return xff.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}
