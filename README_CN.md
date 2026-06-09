<p align="center">
  <img src="assets/logo.png" alt="MedVision-RAG Logo" width="200">
</p>

<h1 align="center">MedVision-RAG</h1>

<p align="center">
  <strong>AI 驱动的药品助手，支持语音交互</strong><br>
  拍一张药品说明书的照片，通过 RAG + 语音即时获取用药信息
</p>

<p align="center">
  <a href="README.md">English</a> · <a href="README_TW.md">繁體中文</a> · <a href="README_ja.md">日本語</a> · <a href="README_ko.md">한국어</a> · <a href="README_es.md">Español</a> · <a href="README_pt-BR.md">Português</a> · <a href="README_ru.md">Русский</a> · <a href="README_fr.md">Français</a> · <a href="README_de.md">Deutsch</a>
</p>

---

## 它能做什么

MedVision-RAG 帮助视障人士和老年用户理解药品信息。对着药盒拍张照，或者上传 PDF / Word 文档，系统会：

1. **提取文字** — 通过 OCR 识别（macOS Vision / Tesseract 回退）
2. **清洗文本** — 使用 Unstructured.io 管道处理空格、断行、项目符号
3. **构建知识库** — 将文本向量化存入 ChromaDB
4. **回答问题** — 自适应 RAG：短文本直接注入上下文，长文本做向量相似度检索
5. **语音播报** — 通过 edge-tts 朗读答案

支持 **网页端**、**微信小程序** 和 **管理后台**（监控聊天日志和数据分析）。

## 功能特性

### 多格式 OCR
- **照片**：药盒、药板、包装 — 直接拍照识别
- **PDF**：支持文字版和扫描版（自动检测，扫描件会渲染为图片后 OCR）
- **Word**：提取正文和表格；文字不足时自动提取嵌入图片做深度 OCR
- **HEIC/HEIF**：iPhone 拍照格式自动转换为 JPEG 后识别

### 自适应 RAG 引擎
- **短文本**（< 1500 字）：Context Stuffing — 将完整说明书注入 LLM 提示词
- **长文本**（>= 1500 字）：向量检索 — 分块存入 ChromaDB，检索 Top-K 相关段落
- **跨药品切换**：用户明确提到其他药品名称时，系统自动切换上下文

### 语音交互
- **网页端**：浏览器原生 Speech Recognition API（零延迟，无 API 消耗）
- **小程序端**：Groq Whisper Large-V3 语音转文字，edge-tts 文字转语音
- **医疗术语纠错**：LLM 对 ASR 输出做后处理，修正被误识别的药品名
- **可打断播报**：按下说话按钮立即停止正在播放的 TTS

### 风险监控
- **关键词检测**：在 `risk_keywords.json` 中配置风险关键词
- **聊天日志审计**：所有对话记录存入 MySQL，可在后台查看
- **邮件告警**：触发风险关键词时自动发送邮件通知（可配置）
- **管理后台**：Streamlit 实时监控仪表盘，支持 IP 白名单保护

### 无障碍设计
- 高对比度 UI（WCAG AA 合规）
- 大触摸目标（48px+）
- 全语音驱动工作流，适合视障用户
- 中英文一键切换，AI 回答和语音播报同步切换

## 系统架构

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  网页前端    │────▶│  Java 后端       │────▶│  Python AI 服务  │
│  :5174      │     │  Spring Boot     │     │  FastAPI          │
│  Vue 3      │     │  :8080           │     │  :8001            │
└─────────────┘     │                  │     │                   │
                    │  - REST API      │     │  - OCR (ocrmac)   │
┌─────────────┐     │  - JPA / MySQL   │     │  - ASR (Groq)     │
│  微信小程序  │────▶│  - 鉴权 / CORS   │     │  - RAG (LangChain)│
│             │     │  - IP 白名单     │     │  - TTS (edge-tts) │
└─────────────┘     └────────┬─────────┘     │  - 风险检测       │
                             │               └────────┬──────────┘
                             ▼                        ▼
                    ┌──────────────┐         ┌──────────────┐
                    │   MySQL 8    │         │  ChromaDB    │
                    │   :3306      │         │  （本地存储） │
                    └──────────────┘         └──────────────┘
```

## 环境要求

| 依赖 | 版本 | 说明 |
|:-----|:----:|------|
| Python | 3.10+ | AI 服务运行环境 |
| Java | 17+ | 业务后端运行环境 |
| Maven | 3.8+ | Java 构建工具 |
| MySQL | 8.0+ | 关系型数据存储 |
| macOS（推荐） | 13+ | `ocrmac` 使用 Apple Vision 框架做 OCR |

> **Linux**：可以运行，但需要安装 [Tesseract](https://github.com/tesseract-ocr/tesseract) 替代 `ocrmac`。安装命令：`apt install tesseract-ocr tesseract-ocr-chi-sim`，然后修改 `backend-ai/services/ocr.py`。

## 获取 API Key

你需要一个 **DeepSeek API Key**（必需），以及一个可选的 **Groq API Key**（用于微信小程序语音识别）。

<details>
<summary><strong>如何获取 DeepSeek API Key（必需）</strong></summary>

DeepSeek 提供问答所需的 LLM 模型。

1. 访问 [platform.deepseek.com](https://platform.deepseek.com/)
2. 注册并登录
3. 在左侧菜单进入 **API Keys**
4. 点击 **创建 API Key**，起个名字（如 "MedVision"）
5. 立即复制 Key（以 `sk-` 开头，只显示一次）

**费用**：默认使用的 `deepseek-v4-flash` 模型非常便宜，一整天的开发测试通常不到 ¥0.01。

</details>

<details>
<summary><strong>如何获取 Groq API Key（可选 — 仅小程序需要）</strong></summary>

Groq 通过 LPU 硬件提供高速 Whisper 语音识别。

1. 访问 [console.groq.com](https://console.groq.com/)
2. 用 GitHub 或 Google 账号注册
3. 在左侧菜单进入 **API Keys**
4. 点击 **Create API Key**
5. 复制 Key（以 `gsk-` 开头）

**费用**：免费额度包含充足的 Whisper 使用量。网页端使用浏览器原生语音 API，**不消耗** Groq 额度 — 只有微信小程序使用 Groq。

</details>

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/Ha1baraA11/MedVision_RAG.git
cd MedVision_RAG
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

用任意文本编辑器打开 `.env`，填入你的配置：

```bash
# macOS
open -e .env

# VS Code
code .env
```

| 变量 | 必填 | 说明 |
|------|:----:|------|
| `MYSQL_PASSWORD` | **是** | 你的 MySQL root 密码 |
| `DEEPSEEK_API_KEY` | **是** | 从 [platform.deepseek.com](https://platform.deepseek.com/) 获取 |
| `DEEPSEEK_BASE_URL` | 否 | 默认 `https://api.deepseek.com` |
| `GROQ_API_KEY` | 小程序需要 | 从 [console.groq.com](https://console.groq.com/) 获取 |
| `SMTP_SERVER` | 否 | SMTP 服务器地址（如 `smtp.qq.com`） |
| `SMTP_PORT` | 否 | SMTP 端口（QQ 邮箱用 `465`） |
| `SMTP_USER` | 否 | 发件人邮箱 |
| `SMTP_PASSWORD` | 否 | SMTP 授权码（不是邮箱登录密码） |
| `SMTP_RECEIVER` | 否 | 收件人邮箱 |
| `INTERNAL_TOKEN` | 否 | Java ↔ Python 服务间鉴权 Token |

> **说明**：`MYSQL_PASSWORD` 是系统启动唯一真正必需的凭证。其他配置都有安全的默认值或优雅降级。

<details>
<summary><strong>如何获取 QQ 邮箱 SMTP 授权码</strong></summary>

1. 登录 [QQ 邮箱](https://mail.qq.com/) → 设置 → 账户
2. 找到 **POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV 服务**
3. 开启 **IMAP/SMTP 服务**
4. 按提示用手机发短信验证，获取 **授权码**
5. 将授权码填入 `SMTP_PASSWORD`（不是 QQ 密码）

</details>

### 3. 配置 Python 环境

```bash
cd backend-ai

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖（首次约 2 分钟）
pip install -r requirements.txt
```

首次运行会从 HuggingFace 下载 `bge-small-zh-v1.5` 嵌入模型（约 90MB）。

### 4. 配置 Java 环境

```bash
cd backend-java

# 下载依赖并编译（首次约 3 分钟）
mvn clean install -DskipTests
```

### 5. 初始化数据库

```bash
mysql -u root -p < sql/init.sql
```

这条命令会创建：
- 数据库 `medvision`（UTF8MB4 编码）
- 表 `medicines` — 药品信息和说明书全文
- 表 `chat_logs` — 对话历史和分析数据
- 表 `admin_users` — 管理员账号

默认管理员账号（`admin` / `admin`）在 Java 后端首次启动时自动创建。

> **提示**：如果跳过这一步，Spring Boot 的 `hibernate.ddl-auto=update` 会在启动时自动建表。SQL 脚本用于显式管理表结构，也便于生产环境部署。

## 使用

### 一键启动（全部服务）

```bash
./start_all.sh
```

该脚本按依赖顺序启动所有服务，等待每个服务就绪后输出状态。日志分别写入 `backend-ai/service.log`、`backend-java/backend.log` 和 `dashboard.log`。

### 手动启动（3 个终端窗口）

**终端 1 — Python AI 服务**（启动最慢，优先启动）

```bash
cd backend-ai
source venv/bin/activate
python main.py
```

等待出现：`Uvicorn running on http://0.0.0.0:8001`

> 首次启动会下载并缓存嵌入模型（`bge-small-zh-v1.5`）。后续启动约 3 秒。

**终端 2 — Java 后端**

```bash
cd backend-java
mvn spring-boot:run
```

等待出现：`Started MedVisionApplication in X.XXX seconds`

> Maven 首次运行会下载依赖。后端会自动创建数据库表和默认管理员账号。

**终端 3 — 网页前端**

```bash
cd frontend
python3 -m http.server 5174
```

浏览器访问 http://localhost:5174。

**可选 — 管理后台**

```bash
streamlit run admin_dashboard.py --server.port 8502
```

访问 http://localhost:8502，登录：`admin` / `admin`。

### 一键停止

```bash
./stop_all.sh
```

或手动停止：

```bash
lsof -t -i:5174 -i:8080 -i:8001 -i:8502 | xargs kill -9
```

## 微信小程序

### 配置步骤

1. 下载并安装 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 打开工具，点击 **导入项目**
3. 选择 `frontend-wechat/` 目录
4. 选择 **测试号** 或游客模式
5. 编辑 `frontend-wechat/config.js`：

```js
const API_CANDIDATES = [
  'http://192.168.x.x:8080',  // 替换为你电脑的局域网 IP
];
```

### 查找局域网 IP

```bash
# macOS
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr "IPv4"
```

### 真机调试

1. 确保手机和电脑在 **同一 Wi-Fi 网络** 下
2. 在微信开发者工具中点击 **真机调试**
3. 扫描二维码
4. 如果连接失败，检查：
   - 电脑防火墙是否放行了 `8080` 端口
   - `config.js` 中的 IP 是否正确（不是 `localhost`）
   - Java 后端是否已启动

## 配置项

### 切换 LLM 模型

编辑 `backend-ai/core/config.py`：

```python
llm = ChatOpenAI(
    model="deepseek-v4-flash",   # 在这里切换模型
    api_key=API_KEY,
    base_url=BASE_URL,
    temperature=0.3               # 0.0 = 确定性，1.0 = 创造性
)
```

可选的 DeepSeek 模型：
| 模型 | 速度 | 费用 | 推荐场景 |
|------|:----:|:----:|----------|
| `deepseek-v4-flash` | 快 | 极低 | 开发、演示（默认） |
| `deepseek-v4` | 中 | 低 | 需要更高质量回答时 |

### OCR 引擎

默认使用 `ocrmac`（macOS Vision）。Linux 上切换到 Tesseract：

```bash
# 安装 Tesseract 及中文支持
sudo apt install tesseract-ocr tesseract-ocr-chi-sim

# 安装 Python 封装
pip install pytesseract
```

然后修改 `backend-ai/services/ocr.py`，将 `ocrmac` 替换为 `pytesseract`。

### 嵌入模型

默认使用 `BAAI/bge-small-zh-v1.5`（中文医学文本优化，约 90MB），在 CPU 上本地运行，不需要 API 调用。如需更换：

```python
# backend-ai/core/config.py
embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",  # 在这里更换模型
    model_kwargs={"local_files_only": True, "device": "cpu"}
)
```

> 首次使用时将 `local_files_only` 改为 `False` 以从 HuggingFace 下载。

### 风险关键词

编辑 `risk_keywords.json` 添加或删除触发词：

```json
{
  "keywords": ["过量", "中毒", "过敏", "禁忌", "副作用", "..."]
}
```

当用户问题或 AI 回答中出现任何关键词时，系统会记录事件并在配置了邮件的情况下发送告警。

### 管理后台安全

管理后台通过 IP 白名单限制访问。在 `backend-java/src/main/resources/application.properties` 中配置：

```properties
admin.security.enabled=true
admin.security.ip-whitelist=127.0.0.1,::1
```

远程访问时需将你的 IP 加入白名单。

### 嵌入模型首次下载

嵌入模型首次下载后会缓存在本地。如需强制重新下载：

```bash
cd backend-ai
source venv/bin/activate
python -c "from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='BAAI/bge-small-zh-v1.5')"
```

## API 接口

### Python AI 服务（`:8001`）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查 |
| `POST` | `/ocr` | OCR 图片/PDF/Word → 提取文字 |
| `POST` | `/chat` | RAG 问答 |
| `POST` | `/transcribe` | 语音转文字（Groq Whisper） |
| `POST` | `/analyze` | 手动文本分析 |
| `GET` | `/tts` | 文字转语音（edge-tts） |
| `GET` | `/search` | 搜索药品历史 |

### Java 后端（`:8080`）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/medicine/health` | 健康检查 |
| `POST` | `/api/medicine/recognize` | 上传并识别药品说明书 |
| `POST` | `/api/medicine/chat` | 代理转发到 AI 服务 |
| `GET` | `/api/medicine/list` | 列出所有已存储药品 |
| `GET` | `/api/medicine/chat-logs` | 聊天日志（管理员） |
| `GET` | `/api/medicine/analytics` | 使用分析（管理员） |
| `POST` | `/api/medicine/admin/login` | 管理员登录 |

## 测试

```bash
# Python 单元测试（17 个测试，约 0.2 秒）
cd backend-ai
source venv/bin/activate
python -m pytest tests/ -v

# Java 单元测试（6 个测试）
cd backend-java
mvn test
```

### 测试覆盖

| 模块 | 测试数 | 覆盖内容 |
|------|:------:|----------|
| `check_risk_keywords` | 6 | 命中、缓存、过期、空输入 |
| `smart_rag_search` | 4 | 短文本、长文本、异常降级、边界值 |
| `correct_medical_terms` | 7 | 幻觉过滤、黑名单、LLM 纠错、异常回退 |
| `MedicineController` | 6 | REST 接口 MockMvc 测试 |

## 项目结构

```
MedVision-RAG/
├── frontend/                  # Vue 3 单文件网页应用
│   └── index.html             # 完整前端（848 行）
├── frontend-wechat/           # 微信小程序
│   ├── pages/index/           # 主页面（WXML + JS + WXSS）
│   ├── app.js                 # 小程序入口
│   └── config.js              # API 地址配置
├── backend-java/              # Spring Boot 业务后端
│   ├── src/main/java/com/medvision/
│   │   ├── controller/        # REST 接口
│   │   ├── service/           # 业务逻辑
│   │   ├── entity/            # JPA 实体（Medicine, ChatLog, AdminUser）
│   │   ├── repository/        # Spring Data JPA 仓库
│   │   └── config/            # 安全、CORS、IP 白名单、数据初始化
│   ├── src/test/              # MockMvc 测试
│   └── pom.xml                # Maven 依赖
├── backend-ai/                # FastAPI AI 服务
│   ├── main.py                # 路由入口（约 250 行）
│   ├── core/
│   │   ├── config.py          # 全局单例（LLM、嵌入模型、Groq 客户端）
│   │   ├── logging_config.py  # 结构化日志 + Trace 中间件
│   │   └── security.py        # 内部 Token 验证
│   ├── services/
│   │   ├── ocr.py             # OCR（ocrmac + Tesseract 回退）
│   │   ├── asr.py             # 语音识别（Groq Whisper）
│   │   ├── rag.py             # 自适应 RAG（上下文填充 + 向量检索）
│   │   ├── tts.py             # 语音合成（edge-tts）
│   │   ├── risk.py            # 风险关键词检测 + TTL 缓存
│   │   ├── email.py           # 风险告警邮件（异步线程池）
│   │   ├── intent.py          # 意图分析（当前药品 vs 历史药品）
│   │   ├── search.py          # 药品历史搜索
│   │   └── chat_model.py      # 聊天模型切换
│   ├── models/
│   │   └── schemas.py         # Pydantic 请求模型
│   └── tests/                 # pytest 单元测试
├── admin_dashboard.py         # Streamlit 管理后台
├── risk_keywords.json         # 风险关键词库
├── sql/
│   └── init.sql               # 数据库初始化脚本
├── Package-Insert_Test/       # 测试用药品说明书样本
├── .env.example               # 环境变量模板
├── .gitignore                 # Git 忽略规则
├── start_all.sh               # 一键启动脚本
└── stop_all.sh                # 一键停止脚本
```

## 常见问题

### 安装与启动

**启动报错 `No module named 'ocrmac'`**

`ocrmac` 使用 macOS Vision 框架，仅支持 macOS。Linux 用户需安装 Tesseract：

```bash
sudo apt install tesseract-ocr tesseract-ocr-chi-sim
pip install pytesseract
```

然后修改 `backend-ai/services/ocr.py` 使用 `pytesseract`。

**Java 后端报 `Connection refused`**

MySQL 未运行或密码错误。

```bash
# 检查 MySQL 状态
mysql -u root -p -e "SELECT 1"

# 验证 .env 中的密码
cat .env | grep MYSQL_PASSWORD
```

**Python 启动时出现 `torchaudio` 警告**

这是关于 VAD（语音活动检测）的非致命警告，系统会回退到无 VAD 模式正常工作。修复方法：`pip install torchaudio`。

**Maven 下载很慢**

在 `~/.m2/settings.xml` 中添加镜像：

```xml
<mirrors>
  <mirror>
    <id>aliyun</id>
    <mirrorOf>central</mirrorOf>
    <url>https://maven.aliyun.com/repository/central</url>
  </mirror>
</mirrors>
```

### 使用

**前端白屏**

打开浏览器开发者工具（F12）→ Console 查看报错。常见原因：
- AI 服务未启动 → 检查 `8001` 端口
- Java 后端未启动 → 检查 `8080` 端口
- CORS 报错 → 确保通过 `localhost:5174` 访问，而不是 `file://`

**小程序无法连接后端**

1. 确认手机和电脑在 **同一 Wi-Fi 网络** 下
2. 检查 `config.js` 中的 IP 是局域网地址（不是 `localhost` 或 `127.0.0.1`）
3. 检查电脑防火墙是否放行了 `8080` 端口
4. 尝试在手机浏览器中访问 `http://你的局域网IP:8080/api/medicine/health`

**语音识别不工作（网页端）**

浏览器要求 HTTPS 或 `localhost` 才能获取麦克风权限。确保通过 `http://localhost:5174` 访问，不要用局域网 IP。

**语音识别不工作（小程序端）**

检查 `.env` 中是否设置了 `GROQ_API_KEY`。修改 `.env` 后需重启 Python AI 服务。

**OCR 返回"未知药品"或乱码**

- 确保照片清晰、光线充足
- 药品名称需在图片中可见
- 对于 PDF，检查是否为扫描版（不可搜索文字）— 系统会自动检测并使用图片 OCR

### 数据库

**如何重置数据库**

```bash
mysql -u root -p -e "DROP DATABASE IF EXISTS medvision;"
mysql -u root -p < sql/init.sql
```

然后重启 Java 后端以重新创建默认管理员账号。

**如何修改管理员密码**

使用管理后台（http://localhost:8502）登录后修改，或直接在 MySQL 中更新：

```sql
USE medvision;
UPDATE admin_users SET password_hash = '$2a$10$...' WHERE username = 'admin';
```

生成 BCrypt 哈希：

```python
from passlib.hash import bcrypt
print(bcrypt.hash("你的新密码"))
```

## 开源协议

MIT
