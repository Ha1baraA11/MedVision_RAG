package com.medvision.repository;

import com.medvision.entity.Medicine;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * 药品数据仓库 - 提供药品表的 CRUD 及自定义查询操作。
 * <p>
 * 继承 JpaRepository，自动获得基本的增删改查能力。
 */
public interface MedicineRepository extends JpaRepository<Medicine, Long> {

    /**
     * 根据药品名称进行模糊查询，支持分页。
     * <p>
     * Spring Data JPA 根据方法名自动生成 LIKE 查询 SQL。
     * 使用分页参数防止大结果集导致 OOM。
     *
     * @param name     药品名称关键字（模糊匹配）
     * @param pageable 分页参数（页码、每页条数）
     * @return 匹配的药品分页结果
     */
    Page<Medicine> findByNameContaining(String name, Pageable pageable);
}
