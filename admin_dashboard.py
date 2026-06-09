"""
MedVision-RAG 管理后台仪表盘（Streamlit 版）
============================================
功能模块：
  - 实时业务监控：语音识别 vs 语义校准比对、请求量/成功率/延迟统计
  - 检索链路分析：向量检索 Top-K 文本块及相似度评分可视化
  - 药品库存管理：药品列表、咨询热度排行、24H 趋势
  - 合规风险审计：敏感词监控、违规记录高亮、触发统计

启动方式: streamlit run admin_dashboard.py
"""

import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import os
from dotenv import load_dotenv

load_dotenv()

# ========================================
# 数据库连接配置
# ========================================
MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "port": int(os.environ.get("MYSQL_PORT", 3306)),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DATABASE", "medvision")
}

CHROMA_PERSIST_DIR = "./chroma_db"

# ========================================
# 数据库连接 (优雅降级: 无库时使用 Mock 数据)
# ========================================
try:
    from sqlalchemy import create_engine, text
    import pymysql
    import urllib.parse
    
    # 构建连接字符串 (安全编码密码)
    safe_password = urllib.parse.quote_plus(MYSQL_CONFIG['password'])
    db_url = f"mysql+pymysql://{MYSQL_CONFIG['user']}:{safe_password}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}"
    engine = create_engine(db_url, echo=False)
    
    # 立即测试数据库连接
    with engine.connect() as conn:
        pass
        
    DB_AVAILABLE = True
except Exception as e:
    # 将错误信息打印到控制台
    print(f"[Warning] MySQL 连接失败: {e}，使用 Mock 数据模式")
    # 同时也显示在页面上，方便调试
    import streamlit as st
    st.toast(f"MySQL 连接异常: {str(e)}，已切换至 Mock 模式", icon="⚠️")
    
    engine = None
    DB_AVAILABLE = False

# ChromaDB 连接
try:
    import chromadb
    chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    CHROMA_AVAILABLE = True
except Exception as e:
    print(f"[Warning] ChromaDB 连接失败: {e}")
    chroma_client = None
    CHROMA_AVAILABLE = False

# ========================================
# 登录认证模块
# ========================================
import bcrypt

def _table_exists(table_name):
    """检查 MySQL 表是否存在"""
    if not DB_AVAILABLE:
        return False
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = :db AND table_name = :tbl"),
                {"db": MYSQL_CONFIG["database"], "tbl": table_name}
            ).scalar()
            return result > 0
    except Exception:
        return False

def _get_admin_user(username):
    """从 admin_users 表查询管理员，返回 (id, username, password_hash, real_name, status, failed_attempts, lock_time)"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT id, username, password_hash, real_name, status, failed_attempts, lock_time FROM admin_users WHERE username = :u"),
                {"u": username}
            ).fetchone()
            return result
    except Exception:
        return None

def _record_login_failure(username):
    """记录登录失败，超过5次锁定15分钟"""
    try:
        with engine.connect() as conn:
            conn.execute(
                text("UPDATE admin_users SET failed_attempts = failed_attempts + 1 WHERE username = :u"),
                {"u": username}
            )
            row = conn.execute(
                text("SELECT failed_attempts FROM admin_users WHERE username = :u"),
                {"u": username}
            ).fetchone()
            if row and row[0] >= 5:
                conn.execute(
                    text("UPDATE admin_users SET lock_time = DATE_ADD(NOW(), INTERVAL 15 MINUTE) WHERE username = :u"),
                    {"u": username}
                )
            conn.commit()
    except Exception:
        pass

def _record_login_success(username):
    """登录成功，重置失败次数"""
    try:
        with engine.connect() as conn:
            conn.execute(
                text("UPDATE admin_users SET failed_attempts = 0, lock_time = NULL, last_login_time = NOW() WHERE username = :u"),
                {"u": username}
            )
            conn.commit()
    except Exception:
        pass

def _show_login_page():
    """渲染登录页面（纯 Streamlit 组件，无 HTML div 嵌套）"""
    # 隐藏 Streamlit 默认顶栏
    st.markdown("""
    <style>
        header[data-testid="stHeader"] { display: none; }
        .block-container { padding-top: 6rem; }
    </style>
    """, unsafe_allow_html=True)

    # 前置检查：admin_users 表是否存在
    if not DB_AVAILABLE:
        st.error("数据库连接失败，请检查 MySQL 服务是否启动")
        st.stop()

    if not _table_exists("admin_users"):
        st.error("admin_users 表不存在，请先启动 Java 后端以自动建表")
        st.info("启动命令: cd backend-java && mvn spring-boot:run")
        st.stop()

    # 标题
    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        st.markdown("## MedVision 管理后台")
        st.caption("请登录以继续")

        # 登录表单
        with st.form("login_form"):
            username = st.text_input("用户名", placeholder="请输入用户名", label_visibility="collapsed")
            password = st.text_input("密码", type="password", placeholder="请输入密码", label_visibility="collapsed")
            submitted = st.form_submit_button("登 录", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("请输入用户名和密码")
            else:
                user = _get_admin_user(username)
                if user is None:
                    st.error("用户名或密码错误")
                elif user[4] == 0:  # status == 0
                    st.error("账号已被禁用")
                elif user[6] and user[6] > datetime.now():  # lock_time > now
                    remaining = (user[6] - datetime.now()).seconds // 60
                    st.error(f"账号已锁定，请 {remaining + 1} 分钟后重试")
                else:
                    try:
                        password_match = bcrypt.checkpw(password.encode("utf-8"), user[2].strip().encode("utf-8"))
                    except Exception as e:
                        st.error(f"密码验证异常: {e}")
                        password_match = False
                    if not password_match:
                        _record_login_failure(username)
                        st.error("用户名或密码错误")
                    else:
                        _record_login_success(username)
                        st.session_state["authenticated"] = True
                        st.session_state["admin_username"] = username
                        st.session_state["admin_real_name"] = user[3] or username
                        st.rerun()

# ========================================
# Mock 数据生成器 (中文医疗场景)
# ========================================
MOCK_MEDICINES = [
    {"id": 1, "name": "阿莫西林胶囊", "create_time": datetime.now() - timedelta(days=5)},
    {"id": 2, "name": "布洛芬缓释片", "create_time": datetime.now() - timedelta(days=3)},
    {"id": 3, "name": "头孢克肟分散片", "create_time": datetime.now() - timedelta(days=2)},
    {"id": 4, "name": "奥美拉唑肠溶胶囊", "create_time": datetime.now() - timedelta(days=1)},
    {"id": 5, "name": "氯雷他定片", "create_time": datetime.now()},
]

MOCK_QUESTIONS = [
    "这个药怎么吃",
    "一次吃几粒",
    "饭前还是饭后吃",
    "有什么副作用",
    "能和阿莫西林一起吃吗",
    "过敏了怎么办",
    "禁忌症有哪些",
    "儿童可以用吗",
    "孕妇能吃吗",
]

RISK_KEYWORDS = ["副作用", "过敏", "禁忌", "禁用", "不良反应", "慎用", "忌用"]

# ========================================
# 风险词配置持久化 (MySQL System Config)
# ========================================
import json
import os

def load_risk_keywords() -> list:
    """
    加载风险关键词配置（三级降级策略）：
    1. 优先从 MySQL system_config 表读取
    2. 降级到本地 risk_keywords.json 文件
    3. 最终降级到代码中的默认列表
    """
    if DB_AVAILABLE and engine:
        try:
            with engine.connect() as conn:
                query = text("SELECT config_value FROM system_config WHERE config_key = 'risk_keywords'")
                result = conn.execute(query).fetchone()
                if result:
                    # result[0] 是 JSON 字符串或 dict (取决于驱动)
                    config_data = result[0]
                    if isinstance(config_data, str):
                        config_data = json.loads(config_data)
                    return config_data.get("keywords", RISK_KEYWORDS)
        except Exception as e:
            print(f"[Warning] 从 MySQL 加载配置失败: {e}")
            pass
            
    # 降级：尝试从本地 JSON 加载 (作为备份)
    RISK_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "risk_keywords.json")
    if os.path.exists(RISK_CONFIG_FILE):
        try:
            with open(RISK_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("keywords", RISK_KEYWORDS)
        except Exception:
            pass
            
    return RISK_KEYWORDS.copy()

def save_risk_keywords(keywords: list) -> bool:
    """
    保存风险关键词配置（双写策略）：
    1. 优先写入 MySQL（UPSERT 语法，存在则更新）
    2. 同时备份到本地 JSON 文件
    """
    success = False
    
    # 1. 优先保存到 MySQL
    if DB_AVAILABLE and engine:
        try:
            config_data = {"keywords": keywords, "updated_at": datetime.now().isoformat()}
            json_str = json.dumps(config_data, ensure_ascii=False)
            
            with engine.connect() as conn:
                # 使用 UPSERT 语法
                query = text("""
                    INSERT INTO system_config (config_key, config_value, description)
                    VALUES ('risk_keywords', :val, '风险预警关键词列表')
                    ON DUPLICATE KEY UPDATE config_value = :val
                """)
                conn.execute(query, {"val": json_str})
                conn.commit()
            success = True
        except Exception as e:
            print(f"[Error] 保存配置到 MySQL 失败: {e}")
    
    # 2. 同时保存到本地 JSON 作为备份
    try:
        RISK_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "risk_keywords.json")
        with open(RISK_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"keywords": keywords, "updated_at": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
        # 如果 MySQL 失败但文件成功，也算部分成功
        if not success:
            print("[Info] 已降级保存到本地文件")
            success = True
    except Exception as e:
        print(f"[Error] 保存配置到本地文件失败: {e}")
        
    return success

def check_response_risk(response: str, keywords: list = None) -> bool:
    """检查文本是否包含风险关键词（支持传入自定义关键词列表）"""
    if keywords is None:
        keywords = load_risk_keywords()
    return any(kw in str(response) for kw in keywords)


# ========================================
# 分页组件 (通用)
# ========================================
def paginated_dataframe(df, key: str, page_size: int = 10, height: int = 400, styled: bool = False, style_func=None):
    """
    通用分页表格组件，支持翻页导航。
    
    Args:
        df: 原始 DataFrame
        key: Streamlit session_state 键名（用于区分不同模块的页码）
        page_size: 每页显示条数
        height: 表格高度
        styled: 是否需要高亮样式
        style_func: 行级样式函数，配合 styled=True 使用
    """
    if df.empty:
        st.info("暂无数据")
        return
    
    total_rows = len(df)
    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    
    # 初始化页码
    page_key = f"page_{key}"
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    
    current_page = st.session_state[page_key]
    # 防止越界
    current_page = min(current_page, total_pages - 1)
    
    # 切片当前页数据
    start_idx = current_page * page_size
    end_idx = min(start_idx + page_size, total_rows)
    page_df = df.iloc[start_idx:end_idx]
    
    # 渲染表格 (st.table 输出普通 HTML，可被 CSS 样式控制)
    if styled and style_func:
        styled_df = page_df.style.apply(style_func, axis=1)
        st.table(styled_df)
    else:
        st.table(page_df)
    
    # 分页导航栏
    nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns([1, 1, 2, 1, 1])
    
    with nav_col1:
        if st.button("⏮ 首页", key=f"first_{key}", disabled=(current_page == 0)):
            st.session_state[page_key] = 0
            st.rerun()
    with nav_col2:
        if st.button("◀ 上一页", key=f"prev_{key}", disabled=(current_page == 0)):
            st.session_state[page_key] = current_page - 1
            st.rerun()
    with nav_col3:
        st.markdown(
            f"<div style='text-align:center; padding-top:8px;'>第 <b>{current_page + 1}</b> / {total_pages} 页　共 {total_rows} 条</div>",
            unsafe_allow_html=True
        )
    with nav_col4:
        if st.button("下一页 ▶", key=f"next_{key}", disabled=(current_page >= total_pages - 1)):
            st.session_state[page_key] = current_page + 1
            st.rerun()
    with nav_col5:
        if st.button("末页 ⏭", key=f"last_{key}", disabled=(current_page >= total_pages - 1)):
            st.session_state[page_key] = total_pages - 1
            st.rerun()


def section_header_with_refresh(title: str, key: str):
    """
    渲染带独立刷新按钮的表格标题行。
    
    点击按钮后标记该表格需要重新加载数据，
    同时通过 st.toast 给出轻量提示，并显示上次刷新时间。
    """
    refresh_key = f"refresh_ts_{key}"
    last_refresh_key = f"last_refresh_{key}"
    if refresh_key not in st.session_state:
        st.session_state[refresh_key] = 0
    
    col_title, col_time, col_btn = st.columns([4, 2, 1])
    with col_title:
        st.subheader(title)
    with col_time:
        # 显示上次刷新时间（纯文本版，无 emoji 干扰）
        if last_refresh_key in st.session_state:
            st.caption(f"最近刷新时间: {st.session_state[last_refresh_key]}")
    with col_btn:
        # 使用 Streamlit 1.37+ 原生的 icon 参数实现清爽的 Material 符号，替换原有的 emoji
        if st.button("刷新", key=f"refresh_btn_{key}", use_container_width=True, icon=":material/refresh:"):
            st.session_state[refresh_key] += 1
            st.session_state[last_refresh_key] = datetime.now().strftime("%H:%M:%S")
            # 移除 toast 中的 AI 风 emoji，改用标准的 Material Info 图标
            st.toast(f"{title} 数据已更新", icon=":material/info:")
            st.rerun()


def _load_chat_logs_fresh(caller: str, risky_only: bool = False) -> pd.DataFrame:
    """直接加载聊天记录（不缓存），带调试日志"""
    now = datetime.now().strftime("%H:%M:%S")
    df = load_chat_logs(risky_only=risky_only)
    print(f"[DEBUG][{now}] _load_chat_logs_fresh(caller={caller}) => {len(df)} 条记录")
    return df


def _load_medicines_fresh(caller: str) -> pd.DataFrame:
    """直接加载药品列表（不缓存），带调试日志"""
    now = datetime.now().strftime("%H:%M:%S")
    df = load_medicines()
    print(f"[DEBUG][{now}] _load_medicines_fresh(caller={caller}) => {len(df)} 条记录")
    return df


def _load_top_medicines_fresh(caller: str):
    """直接加载热门药品（不缓存），带调试日志"""
    now = datetime.now().strftime("%H:%M:%S")
    df = load_top_medicines()
    print(f"[DEBUG][{now}] _load_top_medicines_fresh(caller={caller}) => {len(df) if df is not None else 0} 条")
    return df


def generate_mock_chat_logs(n: int = 20) -> pd.DataFrame:
    """生成模拟聊天记录（数据库不可用时的降级方案）"""
    logs = []
    for i in range(n):
        med = random.choice(MOCK_MEDICINES)
        raw_asr = random.choice(MOCK_QUESTIONS)
        # 模拟 ASR 识别错误
        asr_errors = {"阿莫西林": "阿木西林", "布洛芬": "部落粉", "头孢": "头炮", "副作用": "福作用"}
        corrupted_asr = raw_asr
        for correct, wrong in asr_errors.items():
            if correct in raw_asr and random.random() > 0.5:
                corrupted_asr = raw_asr.replace(correct, wrong)
                break
        
        # 模拟 AI 回复 (部分包含风险词)
        responses = [
            "根据说明书，这个药一次吃1-2粒，每日3次。",
            "建议饭后半小时服用，减少胃肠道刺激。",
            "常见副作用包括恶心、头晕，如有不适请停药。",
            "青霉素过敏者禁用此药物。",
            "儿童用量需减半，6岁以下儿童禁忌使用。",
            "与其他抗生素合用时需注意不良反应。",
        ]
        response = random.choice(responses)
        
        # 判断风险等级
        is_risky = any(kw in response for kw in RISK_KEYWORDS)
        
        logs.append({
            "timestamp": datetime.now() - timedelta(minutes=random.randint(1, 1440)),
            "user_id": f"user_{random.randint(1001, 1010)}",
            "medicine_id": med["id"],
            "medicine_name": med["name"],
            "raw_asr": corrupted_asr,
            "corrected_text": raw_asr,
            "response": response,
            "response_status": "SUCCESS" if random.random() > 0.1 else "TIMEOUT",
            "is_risky": is_risky,
            "latency_ms": random.randint(200, 1500),
        })
    
    df = pd.DataFrame(logs)
    df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)
    return df

def generate_mock_chunks(medicine_name: str) -> List[Dict]:
    """生成模拟的向量检索结果（ChromaDB 不可用时的降级方案）"""
    chunks = [
        {"content": f"【{medicine_name}】用法用量：口服。成人一次0.5g，每6~8小时1次，一日剂量不超过4g。", "score": 0.92},
        {"content": f"【{medicine_name}】适应症：用于敏感菌所致的呼吸道感染、泌尿道感染、皮肤软组织感染。", "score": 0.87},
        {"content": f"【{medicine_name}】不良反应：常见恶心、呕吐、腹泻等胃肠道反应。皮疹较为常见。", "score": 0.81},
    ]
    return chunks

# ========================================
# 数据加载函数
# ========================================

# Java 后端 API 基础地址
JAVA_API_BASE = "http://localhost:8080/api/medicine"

def load_chat_logs(risky_only: bool = False) -> pd.DataFrame:
    """
    从 Java 后端 API 加载聊天记录。
    将 Spring Page 格式的响应转换为 DataFrame，并重命名列以匹配 Dashboard 格式。
    Args:
        risky_only: 是否只加载风险记录
    """
    import requests
    
    endpoint = f"{JAVA_API_BASE}/chat-logs/risky" if risky_only else f"{JAVA_API_BASE}/chat-logs"
    
    try:
        print(f"[DEBUG] 正在请求: {endpoint}")
        resp = requests.get(endpoint, timeout=5)
        print(f"[DEBUG] 响应状态: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            # Spring Page 格式：数据在 content 字段中
            records = data.get("content", data) if isinstance(data, dict) else data
            print(f"[DEBUG] 数据条数: {len(records) if records else 0}")
            if records and len(records) > 0:
                df = pd.DataFrame(records)
                # 重命名列以匹配 Dashboard 期望的格式
                column_mapping = {
                    "createTime": "timestamp",
                    "userId": "user_id",
                    "medicineId": "medicine_id",
                    "medicineName": "medicine_name",
                    "chatModel": "chat_model",
                    "rawAsr": "raw_asr",
                    "correctedText": "corrected_text",
                    "response": "response",
                    "responseStatus": "response_status",
                    "latencyMs": "latency_ms",
                    "isRisky": "is_risky"
                }
                df = df.rename(columns=column_mapping)
                if "chat_model" not in df.columns:
                    df["chat_model"] = "未记录"
                else:
                    df["chat_model"] = df["chat_model"].fillna("未记录")
                # 转换时间格式 (使用 ISO8601 以兼容毫秒格式)
                if "timestamp" in df.columns:
                    df["timestamp"] = pd.to_datetime(df["timestamp"], format='ISO8601')
                return df.sort_values("timestamp", ascending=False).reset_index(drop=True)
        else:
            print(f"[DEBUG] API 响应错误: {resp.text[:200]}")
    except Exception as e:
        print(f"[Warning] 无法从 Java API 加载聊天记录: {e}")
    
    # 不使用 Mock 数据，返回空 DataFrame
    return pd.DataFrame()


def load_top_medicines() -> pd.DataFrame:
    """从 Java 后端 API 加载药品查询热度排行数据"""
    import requests
    
    try:
        resp = requests.get(f"{JAVA_API_BASE}/analytics/top-medicines", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                return pd.DataFrame(data)
    except Exception as e:
        print(f"[Warning] 无法加载热度数据: {e}")
    
    # 降级：返回 None
    return None

def load_medicines() -> pd.DataFrame:
    """从 MySQL 数据库加载药品库存列表"""
    if DB_AVAILABLE:
        try:
            with engine.connect() as conn:
                df = pd.read_sql("SELECT id, name, create_time FROM medicines ORDER BY create_time DESC", conn)
            return df
        except Exception as e:
            st.warning(f"数据库查询失败: {e}")
    
    # 不使用 Mock 数据，返回空 DataFrame
    return pd.DataFrame()

def load_chroma_collections() -> List[str]:
    """获取 ChromaDB 向量数据库中的所有知识库 Collection 名称"""
    if CHROMA_AVAILABLE:
        try:
            collections = chroma_client.list_collections()
            return [c.name for c in collections]
        except Exception as e:
            st.warning(f"ChromaDB 查询失败: {e}")
    return ["medicine_1", "medicine_2", "medicine_3"]  # 模拟数据

def search_chroma(collection_name: str, query: str, top_k: int = 3) -> List[Dict]:
    """
    在指定 ChromaDB Collection 中执行向量语义检索。
    使用 LangChain 的 HuggingFaceEmbeddings + Chroma 封装器，
    与后端 Python AI Service 使用完全一致的检索方式。
    """
    if CHROMA_AVAILABLE:
        try:
            # 使用 LangChain 的 Chroma 封装器，与 Backend 完全一致
            from langchain_huggingface import HuggingFaceEmbeddings
            from langchain_community.vectorstores import Chroma
            
            embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5")
            
            # 加载已存在的 Collection (与 Backend 使用相同方式)
            vectorstore = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory="./chroma_db"
            )
            
            # 执行相似度搜索
            results = vectorstore.similarity_search_with_score(query, k=top_k)
            
            chunks = []
            for doc, score in results:
                # LangChain 返回的 score 是距离，需要转换为相似度
                similarity = max(0.0, min(1.0, 1 - score))
                chunks.append({"content": doc.page_content, "score": round(similarity, 3)})
            return chunks
        except Exception as e:
            st.warning(f"向量检索失败: {e}")
    
    # 降级：返回模拟数据
    return generate_mock_chunks("未知药品")

# ========================================
# Streamlit 页面配置
# ========================================
st.set_page_config(
    page_title="MedVision后台系统",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"  # 折叠侧边栏
)

# ========================================
# 登录检查：未登录则显示登录页并终止
# ========================================
if not st.session_state.get("authenticated"):
    _show_login_page()
    st.stop()

# ========================================
# 主题切换逻辑
# ========================================
# 初始化 session state
if "theme" not in st.session_state:
    st.session_state["theme"] = st.query_params.get("theme", "dark")

# 处理 toggle 回调
def _toggle_theme():
    new = "light" if st.session_state["theme"] == "dark" else "dark"
    st.session_state["theme"] = new
    st.query_params["theme"] = new

current_theme = st.session_state["theme"]
is_light = (current_theme == "light")

# 自定义 CSS (毕设亮点: 专业级 UI + 顶部导航)
# 根据主题条件化输出颜色
table_header_bg = "#1e293b" if is_light else "#1e293b"
table_header_fg = "#f8fafc" if is_light else "#f8fafc"
table_row_bg = "#ffffff" if is_light else "#1a1f2e"
table_row_fg = "#1e293b" if is_light else "#e2e8f0"
table_row_alt = "#f8fafc" if is_light else "#232839"
table_border = "#e2e8f0" if is_light else "#334155"
metric_bg = "linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)" if is_light else "linear-gradient(135deg, #1e293b 0%, #334155 100%)"
header_border = "#e2e8f0" if is_light else "#334155"
top_h2_color = "#1e293b" if is_light else "#e2e8f0"
status_color = "#64748b" if is_light else "#94a3b8"
nav_container_bg = "#f8fafc" if is_light else "#161b22"

page_bg = "#ffffff" if is_light else "#0e1117"
page_secondary_bg = "#f0f2f6" if is_light else "#161b22"
page_text = "#1e293b" if is_light else "#fafafa"
page_text_secondary = "#475569" if is_light else "#a3a3a3"

st.markdown(f"""
<style>
    /* ===== 页面背景色覆盖 ===== */
    .stApp {{
        background-color: {page_bg} !important;
        color: {page_text} !important;
    }}
    [data-testid="stSidebar"] {{
        background-color: {page_secondary_bg} !important;
    }}
    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span {{
        color: {page_text} !important;
    }}
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{
        color: {page_text} !important;
    }}
    .stSelectbox label, .stTextInput label, .stTextArea label {{
        color: {page_text} !important;
    }}
    .stSelectbox div[data-baseweb="select"] {{
        background-color: {page_secondary_bg} !important;
        color: {page_text} !important;
    }}
    .stTextInput input, .stTextArea textarea {{
        background-color: {page_secondary_bg} !important;
        color: {page_text} !important;
    }}
    hr {{
        border-color: {table_border} !important;
    }}
    /* expander 样式 */
    .streamlit-expanderHeader {{
        background-color: {page_secondary_bg} !important;
        color: {page_text} !important;
        border: 1px solid {table_border} !important;
        border-radius: 6px !important;
    }}
    .streamlit-expanderContent {{
        background-color: {page_secondary_bg} !important;
        border: 1px solid {table_border} !important;
        border-top: none !important;
    }}
    /* 图表容器 */
    [data-testid="stChart"] {{
        background-color: {page_secondary_bg} !important;
        border-radius: 6px !important;
        padding: 0.5rem !important;
    }}
    /* info/warning/success 提示框 */
    .stAlert {{
        background-color: {page_secondary_bg} !important;
        color: {page_text} !important;
    }}
    /* 进度条文字 */
    .stProgress > div > div > p {{
        color: {page_text} !important;
    }}
    /* button 样式 */
    .stButton > button {{
        background-color: {page_secondary_bg} !important;
        color: {page_text} !important;
        border: 1px solid {table_border} !important;
    }}
    /* selectbox 下拉选项 */
    div[data-baseweb="popover"] ul {{
        background-color: {page_secondary_bg} !important;
        color: {page_text} !important;
    }}

    .main-header {{
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }}
    .metric-card {{
        background: {metric_bg};
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }}

    /* 专业后台系统表格样式优化 (st.table 输出普通 HTML) */
    [data-testid="stTable"] table {{
        font-size: 0.9rem;
        border: 1px solid {table_border};
        border-radius: 6px;
        overflow: hidden;
        border-collapse: separate;
        border-spacing: 0;
        width: 100%;
    }}
    [data-testid="stTable"] table thead tr th {{
        background-color: {table_header_bg} !important;
        color: {table_header_fg} !important;
        font-weight: 600 !important;
        padding: 10px 14px !important;
        border-bottom: 2px solid {table_border} !important;
    }}
    [data-testid="stTable"] table tbody tr td {{
        background-color: {table_row_bg} !important;
        color: {table_row_fg} !important;
        padding: 8px 14px !important;
        border-bottom: 1px solid {table_border} !important;
        line-height: 1.5;
    }}
    [data-testid="stTable"] table tbody tr:nth-child(even) td {{
        background-color: {table_row_alt} !important;
    }}
    [data-testid="stTable"] table tbody tr:hover td {{
        background-color: {'#e2e8f0' if is_light else '#2a3042'} !important;
    }}
    [data-testid="stTable"] table tbody tr td[style*="background-color"] {{
        color: {'#0f172a' if is_light else '#e2e8f0'} !important;
        font-weight: 500;
    }}

    /* 隐藏默认侧边栏按钮 */
    [data-testid="collapsedControl"] {{
        display: none;
    }}
    .top-header {{
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 0.5rem 0;
        margin-bottom: 1rem;
        border-bottom: 2px solid {header_border};
    }}
    .top-header img {{
        width: 60px;
        height: 60px;
    }}
    .top-header h2 {{
        margin: 0;
        color: {top_h2_color};
        font-weight: 600;
    }}
    .status-bar {{
        display: flex;
        gap: 1.5rem;
        font-size: 0.85rem;
        color: {status_color};
        margin-top: 0.5rem;
    }}
    .block-container {{
        padding-top: 1rem !important;
    }}
    header[data-testid="stHeader"] {{
        display: none;
    }}
</style>
""", unsafe_allow_html=True)

# 主题切换 + 登出按钮（页面顶部右侧）
col_spacer, col_logout, col_toggle = st.columns([5, 1, 1])
with col_logout:
    if st.button("退出登录", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state.pop("admin_username", None)
        st.session_state.pop("admin_real_name", None)
        st.rerun()
with col_toggle:
    st.checkbox("浅色主题", value=is_light, key="theme-toggle", on_change=_toggle_theme)

# ========================================
# 顶部导航栏
# ========================================
from streamlit_option_menu import option_menu

# 顶部 Header (居中，无 Logo)
st.markdown("<h1 style='text-align: center; margin-bottom: 0.5rem;'>MedVision 医疗监管系统</h1>", unsafe_allow_html=True)

# 状态栏 (无图标，纯文本)
status_text_color = "#64748b" if is_light else "#94a3b8"
st.markdown(
    f"<div style='text-align: center; color: {status_text_color}; font-size: 0.85em; margin-bottom: 1.5rem; letter-spacing: 0.5px;'>"
    f"当前用户: {st.session_state.get('admin_real_name', '管理员')} &nbsp;&nbsp;|&nbsp;&nbsp; "
    f"系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} &nbsp;&nbsp;|&nbsp;&nbsp; "
    f"数据库: {'正常' if DB_AVAILABLE else '异常'} &nbsp;&nbsp;|&nbsp;&nbsp; "
    f"向量知识库: {'在线' if CHROMA_AVAILABLE else '离线'}"
    f"</div>",
    unsafe_allow_html=True
)

# 水平导航菜单 (专业术语化)
nav_link_color = "#475569" if is_light else "#cbd5e1"
nav_hover = "#dbeafe" if is_light else "#1e3a5f"
nav_icon_color = "#667eea" if is_light else "#93c5fd"
page = option_menu(
    menu_title=None,  # 隐藏菜单标题
    options=["实时业务监控", "检索链路分析", "药品库存管理", "合规风险审计"],
    icons=["activity", "diagram-3", "box-seam", "shield-check"],  # 使用更抽象的图标
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",  # 水平方向
    styles={
        "container": {"padding": "0!important", "background-color": nav_container_bg},
        "icon": {"color": nav_icon_color, "font-size": "18px"},
        "nav-link": {
            "font-size": "16px",
            "text-align": "center",
            "margin": "0px",
            "color": nav_link_color,
            "--hover-color": nav_hover,
            "padding": "10px 20px",
        },
        "nav-link-selected": {"background-color": "#667eea", "color": "white"},
    }
)

st.markdown("---")

# ========================================
# 页面 1: 实时监控台
# ========================================
# ========================================
# 页面 1: 实时业务监控
# ========================================
if page == "实时业务监控":
    st.markdown('<h1 class="main-header">实时业务监控</h1>', unsafe_allow_html=True)
    st.markdown("监控语音识别、语义纠错及知识库问答的全链路业务数据")
    
    # 刷新按钮始终渲染（无论有无数据）
    section_header_with_refresh("语音识别与语义校准比对", "asr_compare")
    
    # 直接加载数据（不使用缓存，确保每次刷新拿到最新数据）
    chat_logs = _load_chat_logs_fresh("asr_compare")
    
    # 检查是否有数据
    if chat_logs.empty:
        st.warning("暂无业务数据")
        st.info("请先在前端进行一次语音问答，记录将自动统计。")
        
        # 显示空指标
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("今日请求量", 0)
        with col2:
            st.metric("系统成功率", "N/A")
        with col3:
            st.metric("平均响应时间", "N/A")
        with col4:
            st.metric("风险会话数", 0)
    else:
        # 顶部指标卡片
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("今日请求量", len(chat_logs))
        with col2:
            success_rate = (chat_logs["response_status"] == "SUCCESS").mean() * 100
            st.metric("系统成功率", f"{success_rate:.1f}%")
        with col3:
            avg_latency = chat_logs["latency_ms"].mean()
            st.metric("平均响应时间", f"{avg_latency:.0f}ms")
        with col4:
            risk_count = chat_logs["is_risky"].sum()
            st.metric("风险会话数", int(risk_count))
        
        st.markdown("---")
        
        # 过滤器
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            status_filter = st.selectbox("状态过滤", ["全部", "SUCCESS", "TIMEOUT", "ERROR"])
        with col_filter2:
            medicine_filter = st.selectbox("药品过滤", ["全部"] + list(chat_logs["medicine_name"].unique()))
        
        # 应用过滤
        filtered_logs = chat_logs.copy()
        if status_filter != "全部":
            filtered_logs = filtered_logs[filtered_logs["response_status"] == status_filter]
        if medicine_filter != "全部":
            filtered_logs = filtered_logs[filtered_logs["medicine_name"] == medicine_filter]
        
        # 显示表格 (高亮 ASR vs LLM 差异)
        display_df = filtered_logs[["timestamp", "user_id", "raw_asr", "corrected_text", "medicine_name", "chat_model", "response_status"]].copy()
        display_df.columns = ["时间", "用户ID", "原始识别(ASR)", "语义校准(LLM)", "药品", "模型", "状态"]
        
        # 高亮 ASR 与 LLM 结果不同的行（绿色背景）
        def highlight_diff(row):
            if row["原始识别(ASR)"] != row["语义校准(LLM)"]:
                return ["background-color: #d4edda; color: #155724"] * len(row)
            return [""] * len(row)
        
        paginated_dataframe(display_df, key="asr_compare", page_size=10, height=400, styled=True, style_func=highlight_diff)
        
        st.info("提示: 绿色高亮行表示语音识别结果经过 LLM 模型校准，修正了潜在的同音异义错误。")

# ========================================
# 页面 2: RAG 链路透视
# ========================================
# ========================================
# 页面 2: 检索链路分析
# ========================================
if page == "检索链路分析":
    st.markdown('<h1 class="main-header">检索链路分析</h1>', unsafe_allow_html=True)
    st.markdown("深入分析向量检索过程，可视化 Top-K 文本块及相似度评分")
    
    # 选择 Knowledge Base
    collections = load_chroma_collections()
    
    col1, col2 = st.columns([1, 2])
    with col1:
        selected_collection = st.selectbox("选择知识库", collections)
    with col2:
        query = st.text_input("模拟用户提问", value="这个药怎么吃？一次吃几粒？")
    
    if st.button("执行检索", type="primary"):
        with st.spinner("正在进行语义检索..."):
            chunks = search_chroma(selected_collection, query, top_k=3)
        
        st.success(f"检索完成。来源: `{selected_collection}`，提取相关片段 3 条。")
        
        # 可视化 Chunks
        st.subheader("检索结果详情")
        
        for i, chunk in enumerate(chunks, 1):
            score = chunk["score"]
            # 根据分数设置符号
            if score >= 0.85:
                indicator = "High"
            elif score >= 0.70:
                indicator = "Medium"
            else:
                indicator = "Low"
            
            with st.expander(f"片段 #{i} (相关度: {score:.3f} - {indicator})", expanded=True):
                st.progress(score, text=f"语义相关度: {score:.1%}")
                st.markdown(f"```\n{chunk['content']}\n```")
        
        # 可视化评分
        st.subheader("相关性评分统计")
        score_df = pd.DataFrame({
            "片段": [f"片段 #{i+1}" for i in range(len(chunks))],
            "评分": [c["score"] for c in chunks]
        })
        st.bar_chart(score_df.set_index("片段"))

# ========================================
# 页面 3: 药品库存管理
# ========================================
if page == "药品库存管理":
    st.markdown('<h1 class="main-header">药品库存与热度管理</h1>', unsafe_allow_html=True)
    
    # 直接加载药品数据（不使用缓存）
    medicines_df = _load_medicines_fresh("medicine_inventory")
    chat_logs = _load_chat_logs_fresh("medicine_inventory")
    top_medicines = _load_top_medicines_fresh("medicine_inventory")
    
    col1, col2 = st.columns(2)
    
    with col1:
        section_header_with_refresh("药品库存列表", "medicine_inventory")
        paginated_dataframe(medicines_df, key="medicine_inventory", page_size=7, height=300)
        st.caption(f"当前库存品种: {len(medicines_df)}")
    
    with col2:
        st.subheader("热门咨询排行 (Top 5)")
        # 统计查询热度 (优先使用 API 数据)
        if top_medicines is not None and len(top_medicines) > 0:
            st.bar_chart(top_medicines.set_index("name")["count"])
        elif "medicine_name" in chat_logs.columns:
            query_counts = chat_logs["medicine_name"].value_counts().head(5)
            st.bar_chart(query_counts)
        else:
            st.info("暂无咨询数据")
    
    st.markdown("---")
    
    # 时间趋势
    st.subheader("咨询趋势分析 (24H)")
    if not chat_logs.empty and "timestamp" in chat_logs.columns:
        chat_logs["hour"] = chat_logs["timestamp"].dt.hour
        hourly_counts = chat_logs.groupby("hour").size()
        st.line_chart(hourly_counts)
    else:
        st.info("数据不足，无法生成趋势图")

# ========================================
# 页面 4: 风险预警中心
# ========================================
# ========================================
# 页面 4: 合规风险审计
# ========================================
if page == "合规风险审计":
    st.markdown('<h1 class="main-header">合规风险审计</h1>', unsafe_allow_html=True)
    st.markdown("监控 AI 回复中的敏感医学术语，确保用药建议合规安全")
    
    # 直接加载数据（不使用缓存）
    chat_logs = _load_chat_logs_fresh("audit_detail")
    
    # 风险关键词设置 (使用 MySQL 持久化存储)
    current_keywords = load_risk_keywords()
    
    with st.expander("敏感词库配置", expanded=False):
        col_edit, col_btn = st.columns([4, 1])
        with col_edit:
            custom_keywords = st.text_area(
                "敏感词列表 (每行一个)",
                value="\n".join(current_keywords),
                height=150,
                key="risk_keywords_input"
            )
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)  # 对齐按钮
            if st.button("保存配置", type="primary"):
                new_keywords = [kw.strip() for kw in custom_keywords.split("\n") if kw.strip()]
                if save_risk_keywords(new_keywords):
                    st.success(f"已更新 {len(new_keywords)} 个敏感词")
                    time.sleep(1)
                    st.rerun()  # 刷新页面显示新结果
                else:
                    st.error("保存失败，请检查数据库连接")
        
        storage_source = "MySQL 数据库" if DB_AVAILABLE else "本地文件 (降级模式)"
        st.caption(f"当前生效敏感词: {len(current_keywords)} 个 | 数据源: {storage_source}")
    
    keywords_list = current_keywords
    
    # 检查是否有数据
    if chat_logs.empty:
        st.warning("暂无审计数据")
        st.info("请先在前端进行语音问答，记录将自动同步。")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("敏感内容会话数", 0)
        with col2:
            st.metric("违规占比", "N/A")
        with col3:
            st.metric("高频敏感词", "无")
    else:
        # 重新计算风险（核心修正：基于用户提问字段）
        def extract_user_question_for_risk(row) -> str:
            """从记录中提取用户提问文本（优先使用纠错后文本，降级到原始 ASR）"""
            # 优先使用 corrected_text，为空则使用 raw_asr
            text = row.get("corrected_text", "")
            if pd.isna(text) or not text.strip():
                text = row.get("raw_asr", "")
            if pd.isna(text):
                text = ""
            return str(text)

        def check_risk_on_user(row) -> bool:
            """检查用户提问是否包含风险关键词"""
            user_text = extract_user_question_for_risk(row)
            return any(kw in user_text for kw in keywords_list)
        
        # 新增一列辅助保存真实提问，方便后续统计高频词
        chat_logs["user_computed_text"] = chat_logs.apply(extract_user_question_for_risk, axis=1)
        chat_logs["is_risky"] = chat_logs.apply(check_risk_on_user, axis=1)
        
        # 统计
        col1, col2, col3 = st.columns(3)
        with col1:
            total_risky = chat_logs["is_risky"].sum()
            st.metric("敏感内容会话数", int(total_risky))
        with col2:
            risk_ratio = total_risky / len(chat_logs) * 100
            st.metric("违规占比", f"{risk_ratio:.1f}%")
        with col3:
            risky_logs = chat_logs[chat_logs["is_risky"]]
            if not risky_logs.empty:
                # 基于用户提问统计高频词
                all_text = " ".join(risky_logs["user_computed_text"])
                most_common_kw = "无"
                max_count = 0
                for kw in keywords_list:
                    count = all_text.count(kw)
                    if count > max_count:
                        max_count = count
                        most_common_kw = kw
                st.metric("高频敏感词", most_common_kw)
            else:
                st.metric("高频敏感词", "无")
        
        st.markdown("---")
        
        # 过滤器
        show_only_risky = st.checkbox("仅显示违规记录", value=True)
        
        if show_only_risky:
            display_logs = chat_logs[chat_logs["is_risky"]]
        else:
            display_logs = chat_logs
        
        # 显示表格
        section_header_with_refresh("审计详情", "audit_detail")
        st.caption(f"共 {len(display_logs)} 条记录")
        
        if display_logs.empty:
            st.info("暂无符合条件的记录")
        else:
            display_df = display_logs[["timestamp", "medicine_name", "corrected_text", "response", "is_risky"]].copy()
            display_df.columns = ["时间", "药品", "用户提问", "AI回复", "违规标记"]
            
            # 高亮违规行（浅红底 + 深红字）
            def highlight_risk(row):
                if row["违规标记"]:
                    return ["background-color: #fee2e2; color: #b91c1c"] * len(row)
                return [""] * len(row)
            
            paginated_dataframe(display_df, key="audit_detail", page_size=10, height=400, styled=True, style_func=highlight_risk)
        
        # 风险词云 (简化版)
        st.subheader("敏感词触发统计")
        keyword_counts = {}
        # 统计同样基于已抽取的 user_computed_text
        for user_text in chat_logs[chat_logs["is_risky"]]["user_computed_text"]:
            for kw in keywords_list:
                if kw in user_text:
                    keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
        
        if keyword_counts:
            kw_df = pd.DataFrame(list(keyword_counts.items()), columns=["敏感词", "触发次数"])
            st.bar_chart(kw_df.set_index("敏感词"))
        else:
            st.info("暂无触发敏感词的记录")

# ========================================
# 页脚
# ========================================
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
    "MedVision System v4.3 | Powered by Streamlit & LangChain"
    "</div>",
    unsafe_allow_html=True
)
