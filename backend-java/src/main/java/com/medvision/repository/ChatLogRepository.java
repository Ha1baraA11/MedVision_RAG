package com.medvision.repository;

import com.medvision.entity.ChatLog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;

/**
 * 聊天日志仓库 - 支持 Admin Dashboard 分页查询
 */
public interface ChatLogRepository extends JpaRepository<ChatLog, Long> {

    /**
     * 按创建时间倒序分页获取所有聊天记录。
     * <p>
     * Spring Data JPA 根据方法名自动生成 SQL，用于 Admin Dashboard 的日志列表展示。
     *
     * @param pageable 分页参数（页码、每页条数）
     * @return 分页后的聊天记录列表
     */
    Page<ChatLog> findByOrderByCreateTimeDesc(Pageable pageable);

    /**
     * 按药品 ID 查询关联的聊天记录，按创建时间倒序排列。
     * <p>
     * 用于查看某个药品的所有历史问答记录。
     *
     * @param medicineId 药品 ID
     * @return 该药品关联的聊天记录列表
     */
    List<ChatLog> findByMedicineIdOrderByCreateTimeDesc(Long medicineId);

    /**
     * 分页查询被标记为风险的对话记录（isRisky = true）。
     * <p>
     * 用于 Admin Dashboard 中的风险对话监控面板。
     *
     * @param pageable 分页参数
     * @return 分页后的风险对话列表
     */
    Page<ChatLog> findByIsRiskyTrueOrderByCreateTimeDesc(Pageable pageable);

    /**
     * 统计每个药品名称的查询次数，按查询次数降序排列。
     * <p>
     * 使用 JPQL 自定义查询，用于 Admin Dashboard 中的药品热度排行榜。
     *
     * @return Object[] 数组，每个元素 [0] 为药品名称，[1] 为查询次数
     */
    @Query("SELECT c.medicineName, COUNT(c) FROM ChatLog c GROUP BY c.medicineName ORDER BY COUNT(c) DESC")
    List<Object[]> countByMedicineName();
}
