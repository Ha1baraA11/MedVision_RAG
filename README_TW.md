<p align="center">
  <img src="assets/logo.png" alt="MedVision-RAG Logo" width="200">
</p>

<h1 align="center">MedVision-RAG</h1>

<p align="center">
  <strong>AI 驅動的語音互動用藥助手</strong><br>
  掃描藥品包裝或上傳說明書，再透過語音或文字取得依據資料生成的回答。
</p>

<p align="center">
  <a href="README.md">English</a> · <a href="README_CN.md">简体中文</a> · <a href="README_ja.md">日本語</a> · <a href="README_ko.md">한국어</a> · <a href="README_es.md">Español</a> · <a href="README_pt-BR.md">Português</a> · <a href="README_ru.md">Русский</a> · <a href="README_fr.md">Français</a> · <a href="README_de.md">Deutsch</a>
</p>

---

## 功能說明

MedVision-RAG 協助視障者、年長使用者及偏好語音操作的使用者了解藥品資訊。將鏡頭對準藥品包裝或上傳 PDF/Word 文件後，系統會：

1. **擷取文字** — 透過 OCR（macOS Vision / Tesseract 備援）
2. **正規化 OCR 文字** — 保留有用的段落結構
3. **建立知識庫** — 將文字向量化存入 ChromaDB
4. **回答問題** — 採用自適應 RAG：短文本直接注入上下文，長文本使用向量相似度搜尋
5. **朗讀答案** — 透過 edge-tts 語音合成

系統支援 **網頁瀏覽器**、**微信小程式**，以及用於監控對話紀錄與分析的**管理後台**。

## 功能特色

### 多格式 OCR
- **照片**：藥品包裝、紙盒、鋁箔包裝 — 直接透過鏡頭拍攝
- **PDF**：支援文字型與掃描型（自動偵測並轉為圖片進行 OCR）
- **Word**：擷取文字與表格；文字不足時自動回退至嵌入圖片 OCR
- **HEIC/HEIF**：iPhone 照片在 OCR 前自動轉換為 JPEG

### 自適應 RAG 引擎
- **短文本**（< 1500 字元）：上下文填充（Context Stuffing）— 將完整文件注入 LLM 提示詞
- **長文本**（>= 1500 字元）：向量搜尋 — 切分為區塊存入 ChromaDB，檢索前 K 筆相關段落
- **跨藥品切換**：當使用者提及不同藥品名稱時，系統自動切換上下文

### 語音互動
- **網頁端**：瀏覽器原生 Speech Recognition API（零延遲、無 API 費用）
- **小程式**：Groq Whisper Large-V3 語音轉文字，edge-tts 文字轉語音
- **醫療術語校正**：LLM 後處理 ASR 輸出，修正誤判的藥品名稱
- **可中斷播放**：按下朗讀按鈕可立即停止正在進行的 TTS

### 風險監控
- **關鍵字偵測**：可於 `risk_keywords.json` 中設定風險關鍵字
- **對話紀錄審計**：所有對話儲存於 MySQL 供審查
- **電子郵件警示**：觸發風險關鍵字時自動發送電子郵件通知（可設定）
- **管理後台**：透過 Streamlit 即時監控，並有 IP 白名單保護

### 無障礙設計
- 高對比度 UI（符合 WCAG AA 標準）
- 大型觸控目標（48px 以上）
- 完整語音驅動工作流程，適用於視障使用者
- 中英文語言切換，AI 回應與 TTS 語音選擇同步切換

## 系統架構

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Web Front  │────▶│  Java Backend    │────▶│  Python AI       │
│  :5174      │     │  Spring Boot     │     │  FastAPI          │
│  Vue 3 CDN  │     │  :8080           │     │  :8001            │
└─────────────┘     │                  │     │                   │
                    │  - REST API      │     │  - OCR (ocrmac)   │
┌─────────────┐     │  - JPA / MySQL   │     │  - ASR (Groq)     │
│  WeChat     │────▶│  - Auth / CORS   │     │  - RAG (LangChain)│
│  Mini App   │     │  - IP Whitelist  │     │  - TTS (edge-tts) │
└─────────────┘     └────────┬─────────┘     │  - Risk Detection │
                             │               └────────┬──────────┘
                             ▼                        ▼
                    ┌──────────────┐         ┌──────────────┐
                    │   MySQL 8    │         │  ChromaDB    │
                    │   :3306      │         │  (local)     │
                    └──────────────┘         └──────────────┘
```

## 環境需求

| 依賴套件 | 版本 | 說明 |
|:-----------|:-------:|-------|
| Python | 3.10+ | AI 服務執行環境 |
| Java | 17+ | 業務後端執行環境 |
| Maven | 3.8+ | Java 建置工具 |
| MySQL | 8.0+ | 關聯式資料儲存 |
| macOS（建議） | 13+ | `ocrmac` 使用 Apple Vision 框架進行 OCR |

> **Linux**：支援，但需使用 [Tesseract](https://github.com/tesseract-ocr/tesseract) 進行 OCR。透過 `apt install tesseract-ocr tesseract-ocr-chi-sim` 安裝，並修改 `backend-ai/services/ocr.py`。

## API 金鑰

你需要一組 **DeepSeek API 金鑰**（必要），以及可選的 **Groq API 金鑰**（微信小程式語音辨識用）。

<details>
<summary><strong>如何取得 DeepSeek API 金鑰（必要）</strong></summary>

DeepSeek 提供問答所使用的 LLM。

1. 前往 [platform.deepseek.com](https://platform.deepseek.com/)
2. 註冊或登入
3. 在左側選單進入 **API Keys**
4. 點擊 **Create API Key**，為其命名（例如 "MedVision"）
5. 立即複製金鑰（以 `sk-` 開頭，不會再次顯示）

**費用**：預設模型 `deepseek-v4-flash` 極為便宜。一整天的開發測試通常花費不到 $0.01。

</details>

<details>
<summary><strong>如何取得 Groq API 金鑰（選用 — 僅限小程式）</strong></summary>

Groq 透過 LPU 硬體上的 Whisper Large-V3 提供快速語音轉文字服務。

1. 前往 [console.groq.com](https://console.groq.com/)
2. 使用 GitHub 或 Google 帳號註冊
3. 在左側選單進入 **API Keys**
4. 點擊 **Create API Key**
5. 複製金鑰（以 `gsk-` 開頭）

**費用**：免費方案包含充裕的 Whisper 用量。網頁前端使用瀏覽器內建語音 API，**不會**消耗 Groq 額度 — 僅微信小程式使用 Groq。

</details>

## 安裝步驟

### 1. 複製專案

```bash
git clone https://github.com/Ha1baraA11/MedVision_RAG.git
cd MedVision_RAG
```

### 2. 設定環境變數

```bash
cp .env.example .env
```

使用任一文字編輯器開啟 `.env` 並填入你的數值：

```bash
# macOS
open -e .env

# VS Code
code .env
```

| 變數 | 必填 | 說明 |
|----------|:--------:|-------------|
| `MYSQL_PASSWORD` | **是** | 你的 MySQL root 密碼 |
| `DEEPSEEK_API_KEY` | **是** | 從 [platform.deepseek.com](https://platform.deepseek.com/) 取得 |
| `DEEPSEEK_BASE_URL` | 否 | 預設：`https://api.deepseek.com` |
| `GROQ_API_KEY` | 小程式用 | 從 [console.groq.com](https://console.groq.com/) 取得 |
| `SMTP_SERVER` | 否 | 風險警示用 SMTP 伺服器（例如 `smtp.qq.com`） |
| `SMTP_PORT` | 否 | SMTP 連接埠（QQ 信箱：`465`） |
| `SMTP_USER` | 否 | 寄件者電子郵件地址 |
| `SMTP_PASSWORD` | 否 | SMTP 授權碼（非信箱密碼） |
| `SMTP_RECEIVER` | 否 | 收件者電子郵件地址 |
| `INTERNAL_TOKEN` | 否 | Java ↔ Python 服務間的驗證權杖 |

> **注意**：`MYSQL_PASSWORD` 是系統啟動唯一真正必要的憑證。其餘項目皆有安全預設值或可正常降級。

<details>
<summary><strong>如何取得 QQ 信箱 SMTP 授權碼</strong></summary>

1. 登入 [mail.qq.com](https://mail.qq.com/) → 設定 → 帳號
2. 找到 **POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV 服務**
3. 啟用 **IMAP/SMTP 服務**
4. 依照簡訊驗證提示取得**授權碼**
5. 使用此授權碼（非 QQ 密碼）作為 `SMTP_PASSWORD`

</details>

### 3. 設定 Python 環境

```bash
cd backend-ai

# 建立虛擬環境
python3 -m venv venv

# 啟用虛擬環境
source venv/bin/activate

# 安裝依賴套件（首次執行約需 2 分鐘）
pip install -r requirements.txt
```

首次執行時會從 HuggingFace 下載 `bge-small-zh-v1.5` 嵌入模型（約 90MB）。

### 4. 設定 Java 環境

```bash
cd backend-java

# 下載依賴套件並編譯（首次執行約需 3 分鐘）
mvn clean install -DskipTests
```

### 5. 初始化資料庫

```bash
mysql -u root -p < sql/init.sql
```

此腳本會建立：
- 資料庫 `medvision`（UTF8MB4）
- 資料表 `medicines` — 藥品資訊與全文
- 資料表 `chat_logs` — 對話紀錄與分析
- 資料表 `admin_users` — 管理員帳號

預設管理員帳號（`admin` / `admin`）會在 Java 後端首次啟動時自動建立。

> **替代方案**：若跳過此步驟，Spring Boot 的 `hibernate.ddl-auto=update` 會在啟動時自動建立資料表。提供 SQL 腳本是為了明確的結構管理與正式環境部署。

## 使用方式

### 快速啟動（一次啟動所有服務）

```bash
./start_all.sh
```

此腳本會按照相依性順序啟動所有服務，等待每個服務就緒後顯示狀態。日誌寫入 `backend-ai/service.log`、`backend-java/backend.log` 及 `dashboard.log`。

### 手動啟動（3 個獨立終端機）

**終端機 1 — Python AI 服務**（最先啟動，速度最慢）

```bash
cd backend-ai
source venv/bin/activate
python main.py
```

等待出現：`Uvicorn running on http://0.0.0.0:8001`

> 首次啟動時會下載並快取嵌入模型（`bge-small-zh-v1.5`）。後續啟動約需 3 秒。

**終端機 2 — Java 後端**

```bash
cd backend-java
mvn spring-boot:run
```

等待出現：`Started MedVisionApplication in X.XXX seconds`

> Maven 首次執行時會下載依賴套件。後端會自動建立資料表與預設管理員帳號。

**終端機 3 — 網頁前端**

```bash
cd frontend
python3 -m http.server 5174
```

在瀏覽器開啟 http://localhost:5174。

**選用 — 管理後台**

```bash
streamlit run admin_dashboard.py --server.port 8502
```

開啟 http://localhost:8502。登入帳號：`admin` / `admin`。

### 停止所有服務

```bash
./stop_all.sh
```

或手動執行：

```bash
lsof -t -i:5174 -i:8080 -i:8001 -i:8502 | xargs kill -9
```

## 微信小程式

### 設定

1. 下載並安裝 [微信開發者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 開啟工具，點擊**匯入專案**
3. 選擇 `frontend-wechat/` 目錄
4. 選擇**測試 AppID** 或訪客模式
5. 編輯 `frontend-wechat/config.js`：

```js
const API_CANDIDATES = [
  'http://192.168.x.x:8080',  // 替換為你電腦的區域網路 IP
];
```

### 查詢區域網路 IP

```bash
# macOS
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr "IPv4"
```

### 真機除錯

1. 確認手機與電腦連接至**同一個 Wi-Fi 網路**
2. 在微信開發者工具中，點擊**真機除錯**
3. 使用手機掃描 QR Code
4. 若連線失敗，檢查：
   - 電腦防火牆允許連接埠 `8080`
   - `config.js` 中填入正確的區域網路 IP（非 `localhost`）
   - Java 後端正在執行中

## 設定選項

### 切換 LLM 模型

編輯 `backend-ai/core/config.py`：

```python
llm = ChatOpenAI(
    model="deepseek-v4-flash",   # 在此更改模型
    api_key=API_KEY,
    base_url=BASE_URL,
    temperature=0.3               # 0.0 = 確定性輸出, 1.0 = 創意性輸出
)
```

可用的 DeepSeek 模型：
| 模型 | 速度 | 費用 | 建議用途 |
|-------|:-----:|:----:|-----------------|
| `deepseek-v4-flash` | 快 | 極低 | 開發、展示（預設） |
| `deepseek-v4` | 中 | 低 | 更高品質的回答 |

### OCR 引擎

預設使用 `ocrmac`（macOS Vision）。在 Linux 上切換至 Tesseract：

```bash
# 安裝支援中文的 Tesseract
sudo apt install tesseract-ocr tesseract-ocr-chi-sim

# 安裝 Python 封裝
pip install pytesseract
```

然後修改 `backend-ai/services/ocr.py` 以使用 `pytesseract` 替代 `ocrmac`。

### 嵌入模型

預設模型為 `BAAI/bge-small-zh-v1.5`（針對中文醫療文本優化，約 90MB）。在本機 CPU 上執行，無需 API 呼叫。如需變更：

```python
# backend-ai/core/config.py
embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",  # 在此更改模型
    model_kwargs={"local_files_only": True, "device": "cpu"}
)
```

> 首次使用時將 `local_files_only` 設為 `False` 以從 HuggingFace 下載。

### 風險關鍵字

編輯 `risk_keywords.json` 以新增或移除觸發詞：

```json
{
  "keywords": ["overdose", "poisoning", "allergy", "contraindication", "side effect", "..."]
}
```

當使用者的問題出現已設定的關鍵字時，系統會記錄風險事件，並可發送電子郵件警示。

### 管理後台安全性

管理後台透過 IP 白名單限制存取。在 `backend-java/src/main/resources/application.properties` 中設定：

```properties
admin.security.enabled=true
admin.security.ip-whitelist=127.0.0.1,::1
```

若需遠端存取，請將你的 IP 加入白名單。

### 嵌入模型首次執行設定

嵌入模型在首次下載後會快取於本機。若需強制重新下載：

```bash
cd backend-ai
source venv/bin/activate
python -c "from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='BAAI/bge-small-zh-v1.5')"
```

## API 端點

### Python AI 服務（`:8001`）

| 方法 | 路徑 | 說明 |
|--------|------|-------------|
| `GET` | `/health` | 健康檢查 |
| `POST` | `/ocr` | OCR 圖片/PDF/Word → 擷取文字 |
| `POST` | `/chat` | RAG 問答 |
| `POST` | `/transcribe` | 語音轉文字（透過 Groq 的 Whisper） |
| `POST` | `/analyze` | 手動文字分析 |
| `GET` | `/tts` | 文字轉語音（edge-tts） |
| `GET` | `/search` | 搜尋藥品歷史紀錄 |

### Java 後端（`:8080`）

| 方法 | 路徑 | 說明 |
|--------|------|-------------|
| `GET` | `/api/medicine/health` | 健康檢查 |
| `POST` | `/api/medicine/recognize` | 上傳並辨識藥品說明書 |
| `POST` | `/api/medicine/chat` | 代理至 AI 服務的對話 |
| `GET` | `/api/medicine/list` | 列出所有已儲存的藥品 |
| `GET` | `/api/medicine/chat-logs` | 對話紀錄歷史（管理員） |
| `GET` | `/api/medicine/analytics` | 使用分析（管理員） |
| `POST` | `/api/medicine/admin/login` | 管理員登入 |

## 測試

```bash
# Python 單元測試（17 項測試，約 0.2 秒）
cd backend-ai
source venv/bin/activate
python -m pytest tests/ -v

# Java 單元測試（6 項測試）
cd backend-java
mvn test
```

### 測試覆蓋範圍

| 模組 | 測試數 | 覆蓋內容 |
|--------|:-----:|--------|
| `check_risk_keywords` | 6 | 命中、快取、過期、空輸入 |
| `smart_rag_search` | 4 | 短文本、長文本、錯誤回退、邊界案例 |
| `correct_medical_terms` | 7 | 幻覺過濾、黑名單、LLM 校正、錯誤回退 |
| `MedicineController` | 6 | REST 端點 MockMvc 測試 |

## 專案結構

```
MedVision-RAG/
├── frontend/                  # Vue 3 CDN 單頁網頁應用程式
│   └── index.html             # 完整前端（848 行）
├── frontend-wechat/           # 微信小程式
│   ├── pages/index/           # 主頁面（WXML + JS + WXSS）
│   ├── app.js                 # 應用程式進入點
│   └── config.js              # API 端點設定
├── backend-java/              # Spring Boot 業務後端
│   ├── src/main/java/com/medvision/
│   │   ├── controller/        # REST 端點
│   │   ├── service/           # 業務邏輯
│   │   ├── entity/            # JPA 實體（Medicine, ChatLog, AdminUser）
│   │   ├── repository/        # Spring Data JPA 資料庫存取層
│   │   └── config/            # 安全性、CORS、IP 白名單、資料初始化
│   ├── src/test/              # MockMvc 測試
│   └── pom.xml                # Maven 依賴套件
├── backend-ai/                # FastAPI AI 服務
│   ├── main.py                # 路由進入點（約 250 行）
│   ├── core/
│   │   ├── config.py          # 全域單例（LLM、嵌入模型、Groq 客戶端）
│   │   ├── logging_config.py  # 結構化日誌 + 追蹤中介層
│   │   └── security.py        # 內部權杖驗證
│   ├── services/
│   │   ├── ocr.py             # OCR（ocrmac + Tesseract 備援）
│   │   ├── asr.py             # 語音辨識（Groq Whisper）
│   │   ├── rag.py             # 自適應 RAG（上下文填充 + 向量搜尋）
│   │   ├── tts.py             # 文字轉語音（edge-tts）
│   │   ├── risk.py            # 風險關鍵字偵測 + TTL 快取
│   │   ├── email.py           # 風險警示電子郵件（非同步執行緒池）
│   │   ├── intent.py          # 意圖分析（當前 vs 歷史藥品）
│   │   ├── search.py          # 藥品歷史搜尋
│   │   └── chat_model.py      # 聊天模型切換
│   ├── models/
│   │   └── schemas.py         # Pydantic 請求模型
│   └── tests/                 # pytest 單元測試
├── admin_dashboard.py         # Streamlit 管理後台
├── risk_keywords.json         # 風險關鍵字字典
├── sql/
│   └── init.sql               # 資料庫初始化腳本
├── Package-Insert_Test/       # 測試用藥品說明書範例
├── .env.example               # 環境變數範本
├── .gitignore                 # Git 忽略規則
├── start_all.sh               # 一鍵啟動所有服務
└── stop_all.sh                # 一鍵停止所有服務
```

## 常見問題

### 安裝與啟動

**`No module named 'ocrmac'`**

`ocrmac` 使用 macOS Vision 框架，僅適用於 macOS。在 Linux 上需安裝 Tesseract：

```bash
sudo apt install tesseract-ocr tesseract-ocr-chi-sim
pip install pytesseract
```

然後修改 `backend-ai/services/ocr.py` 以使用 `pytesseract`。

**啟動 Java 後端時出現 `Connection refused`**

MySQL 未執行或密碼錯誤。

```bash
# 檢查 MySQL 狀態
mysql -u root -p -e "SELECT 1"

# 確認 .env 中的密碼與 MySQL root 密碼一致
cat .env | grep MYSQL_PASSWORD
```

**Python 啟動時出現 `torchaudio` 警告**

這是關於 VAD（語音活動偵測）的非致命警告。系統會回退至無 VAD 模式正常運作。修復方式：`pip install torchaudio`。

**Maven 下載速度緩慢**

在 `~/.m2/settings.xml` 中加入鏡像站：

```xml
<mirrors>
  <mirror>
    <id>aliyun</id>
    <mirrorOf>central</mirrorOf>
    <url>https://maven.aliyun.com/repository/central</url>
  </mirror>
</mirrors>
```

### 使用問題

**瀏覽器顯示白畫面**

開啟開發者工具（F12）→ 主控台分頁。常見原因：
- AI 服務未啟動 → 檢查連接埠 `8001`
- Java 後端未啟動 → 檢查連接埠 `8080`
- CORS 錯誤 → 確認透過 `localhost:5174` 存取，而非 `file://`

**小程式無法連線至後端**

1. 確認手機與電腦連接至**同一個 Wi-Fi 網路**
2. 檢查 `config.js` 中填入的是區域網路 IP（非 `localhost` 或 `127.0.0.1`）
3. 檢查電腦防火牆允許連接埠 `8080` 的連入連線
4. 嘗試從手機瀏覽器執行 `curl http://YOUR_LAN_IP:8080/api/medicine/health`

**語音辨識無法使用（網頁端）**

瀏覽器要求 HTTPS 或 `localhost` 才能存取麥克風。確認透過 `http://localhost:5174` 存取頁面，而非區域網路 IP。

**語音辨識無法使用（小程式）**

檢查 `.env` 中已設定 `GROQ_API_KEY`。修改 `.env` 後需重新啟動 Python AI 服務。

**OCR 回傳「未知藥品」或亂碼**

- 確認照片清晰且光線充足
- 藥品名稱應在圖片中可見
- 若為 PDF，檢查檔案是否為掃描圖片（非可搜尋文字） — 系統會自動偵測並使用圖片 OCR

### 資料庫

**如何重置資料庫**

```bash
mysql -u root -p -e "DROP DATABASE IF EXISTS medvision;"
mysql -u root -p < sql/init.sql
```

然後重新啟動 Java 後端以重建預設管理員帳號。

**如何變更管理員密碼**

登入管理後台（http://localhost:8502）後變更，或直接在 MySQL 中更新：

```sql
USE medvision;
UPDATE admin_users SET password_hash = '$2a$10$...' WHERE username = 'admin';
```

使用任一線上工具或 Python 產生 BCrypt 雜湊值：

```python
from passlib.hash import bcrypt
print(bcrypt.hash("your_new_password"))
```

## 授權條款

此儲存庫目前未包含授權檔案。請在散布或於預期範圍外重複使用本專案前新增明確的授權條款。
