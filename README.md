<p align="center">
  <img src="assets/logo.png" alt="MedVision-RAG Logo" width="200">
</p>

<h1 align="center">MedVision-RAG</h1>

<p align="center">
  <strong>AI-powered medication assistant with voice interaction</strong><br>
  Scan a medicine package or upload an insert, then ask grounded questions by voice or text.
</p>

<p align="center">
  <a href="README_CN.md">简体中文</a> · <a href="README_TW.md">繁體中文</a> · <a href="README_ja.md">日本語</a> · <a href="README_ko.md">한국어</a> · <a href="README_es.md">Español</a> · <a href="README_pt-BR.md">Português</a> · <a href="README_ru.md">Русский</a> · <a href="README_fr.md">Français</a> · <a href="README_de.md">Deutsch</a>
</p>

---

## What it does

MedVision-RAG helps visually impaired users, older adults, and anyone who prefers a voice-first workflow understand medicine information. Point your camera at a package or upload a PDF/Word document, and the system:

1. **Extracts text** via OCR (macOS Vision / Tesseract fallback)
2. **Normalizes OCR text** while preserving useful paragraph structure
3. **Builds a knowledge base** by vectorizing the text into ChromaDB
4. **Answers questions** using adaptive RAG — short texts use direct context stuffing, long texts use vector similarity search
5. **Reads the answer aloud** via edge-tts

The system supports **web browser**, **WeChat Mini Program**, and an **admin dashboard** for monitoring chat logs and analytics.

## Features

### Multi-format OCR
- **Photos**: Drug packages, boxes, blisters — directly via camera
- **PDF**: Both text-based and scanned (auto-detects and renders to image for OCR)
- **Word**: Extracts text and tables; falls back to embedded image OCR when text is insufficient
- **HEIC/HEIF**: iPhone photos are auto-converted to JPEG before OCR

### Adaptive RAG Engine
- **Short text** (< 1500 chars): Context Stuffing — injects the full document into the LLM prompt
- **Long text** (>= 1500 chars): Vector search — splits into chunks, stores in ChromaDB, retrieves top-K relevant passages
- **Cross-drug switching**: When the user mentions a different drug by name, the system automatically switches context

### Voice Interaction
- **Web**: Browser-native Speech Recognition API (zero latency, no API cost)
- **Mini Program**: Groq Whisper Large-V3 for speech-to-text, edge-tts for text-to-speech
- **Medical term correction**: LLM post-processes ASR output to fix misrecognized drug names
- **Interruptible playback**: Press the speak button to immediately stop ongoing TTS

### Risk Monitoring
- **Keyword detection**: Configurable risk keywords in `risk_keywords.json`
- **Chat log audit**: All conversations stored in MySQL for review
- **Email alerts**: Automatic email notification when risk keywords are triggered (configurable)
- **Admin dashboard**: Real-time monitoring via Streamlit with IP whitelist protection

### Accessibility
- High contrast UI (WCAG AA compliant)
- Large touch targets (48px+)
- Full voice-driven workflow for visually impaired users
- Chinese/English language toggle with synchronized AI response and TTS voice selection

## Architecture

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

## Requirements

| Dependency | Version | Notes |
|:-----------|:-------:|-------|
| Python | 3.10+ | AI service runtime |
| Java | 17+ | Business backend runtime |
| Maven | 3.8+ | Java build tool |
| MySQL | 8.0+ | Relational data storage |
| macOS (recommended) | 13+ | `ocrmac` uses Apple Vision framework for OCR |

> **Linux**: Supported, but requires [Tesseract](https://github.com/tesseract-ocr/tesseract) for OCR. Install via `apt install tesseract-ocr tesseract-ocr-chi-sim` and modify `backend-ai/services/ocr.py`.

## API Keys

You need a **DeepSeek API Key** (required) and optionally a **Groq API Key** (for WeChat Mini Program speech recognition).

<details>
<summary><strong>How to get DeepSeek API Key (required)</strong></summary>

DeepSeek provides the LLM for question answering.

1. Go to [platform.deepseek.com](https://platform.deepseek.com/)
2. Sign up or log in
3. Navigate to **API Keys** in the left sidebar
4. Click **Create API Key**, give it a name (e.g. "MedVision")
5. Copy the key immediately (it starts with `sk-` and won't be shown again)

**Cost**: The default model `deepseek-v4-flash` is extremely cheap. A full day of development testing typically costs < $0.01.

</details>

<details>
<summary><strong>How to get Groq API Key (optional — Mini Program only)</strong></summary>

Groq provides fast speech-to-text via Whisper Large-V3 on LPU hardware.

1. Go to [console.groq.com](https://console.groq.com/)
2. Sign up with GitHub or Google account
3. Navigate to **API Keys** in the left sidebar
4. Click **Create API Key**
5. Copy the key (starts with `gsk-`)

**Cost**: Free tier includes generous Whisper usage. The web frontend uses the browser's built-in speech API and does **not** consume Groq credits — only the WeChat Mini Program uses Groq.

</details>

## Installation

### 1. Clone

```bash
git clone https://github.com/Ha1baraA11/MedVision_RAG.git
cd MedVision_RAG
```

### 2. Configure environment

```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in your values:

```bash
# macOS
open -e .env

# VS Code
code .env
```

| Variable | Required | Description |
|----------|:--------:|-------------|
| `MYSQL_PASSWORD` | **Yes** | Your MySQL root password |
| `DEEPSEEK_API_KEY` | **Yes** | From [platform.deepseek.com](https://platform.deepseek.com/) |
| `DEEPSEEK_BASE_URL` | No | Default: `https://api.deepseek.com` |
| `GROQ_API_KEY` | Mini Program | From [console.groq.com](https://console.groq.com/) |
| `SMTP_SERVER` | No | SMTP server for risk alerts (e.g. `smtp.qq.com`) |
| `SMTP_PORT` | No | SMTP port (QQ Mail: `465`) |
| `SMTP_USER` | No | Sender email address |
| `SMTP_PASSWORD` | No | SMTP authorization code (not your email password) |
| `SMTP_RECEIVER` | No | Receiver email address |
| `INTERNAL_TOKEN` | No | Auth token between Java ↔ Python services |

> **Note**: `MYSQL_PASSWORD` is the only credential that's truly mandatory for the system to start. Everything else has safe defaults or graceful degradation.

<details>
<summary><strong>How to get QQ Mail SMTP authorization code</strong></summary>

1. Log in to [mail.qq.com](https://mail.qq.com/) → Settings → Account
2. Find **POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV Service**
3. Enable **IMAP/SMTP Service**
4. Follow the SMS verification prompt to get an **authorization code**
5. Use this code (not your QQ password) as `SMTP_PASSWORD`

</details>

### 3. Set up Python environment

```bash
cd backend-ai

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies (first time only, takes ~2 min)
pip install -r requirements.txt
```

The first run will download the `bge-small-zh-v1.5` embedding model (~90MB) from HuggingFace.

### 4. Set up Java environment

```bash
cd backend-java

# Download dependencies and compile (first time only, takes ~3 min)
mvn clean install -DskipTests
```

### 5. Initialize database

```bash
mysql -u root -p < sql/init.sql
```

This creates:
- Database `medvision` (UTF8MB4)
- Table `medicines` — drug information and full text
- Table `chat_logs` — conversation history and analytics
- Table `admin_users` — admin accounts

The default admin account (`admin` / `admin`) is auto-created when the Java backend starts for the first time.

> **Alternative**: If you skip this step, Spring Boot's `hibernate.ddl-auto=update` will auto-create the tables on startup. The SQL script is provided for explicit schema management and production deployments.

## Usage

### Quick start (all services at once)

```bash
./start_all.sh
```

This script starts all services in dependency order, waits for each to be ready, and prints status. Logs are written to `backend-ai/service.log`, `backend-java/backend.log`, and `dashboard.log`.

### Manual start (3 separate terminals)

**Terminal 1 — Python AI Service** (start first, it's the slowest)

```bash
cd backend-ai
source venv/bin/activate
python main.py
```

Wait for: `Uvicorn running on http://0.0.0.0:8001`

> On first startup, the embedding model (`bge-small-zh-v1.5`) will be downloaded and cached. Subsequent starts take ~3 seconds.

**Terminal 2 — Java Backend**

```bash
cd backend-java
mvn spring-boot:run
```

Wait for: `Started MedVisionApplication in X.XXX seconds`

> Maven downloads dependencies on first run. The backend auto-creates database tables and the default admin account.

**Terminal 3 — Web Frontend**

```bash
cd frontend
python3 -m http.server 5174
```

Open http://localhost:5174 in your browser.

**Optional — Admin Dashboard**

```bash
streamlit run admin_dashboard.py --server.port 8502
```

Open http://localhost:8502. Login: `admin` / `admin`.

### Stop all services

```bash
./stop_all.sh
```

Or manually:

```bash
lsof -t -i:5174 -i:8080 -i:8001 -i:8502 | xargs kill -9
```

## WeChat Mini Program

### Setup

1. Download and install [WeChat Developer Tools](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. Open the tool, click **Import Project**
3. Select the `frontend-wechat/` directory
4. Choose **Test AppID** or guest mode
5. Edit `frontend-wechat/config.js`:

```js
const API_CANDIDATES = [
  'http://192.168.x.x:8080',  // replace with your computer's LAN IP
];
```

### Finding your LAN IP

```bash
# macOS
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr "IPv4"
```

### Debugging on real device

1. Make sure your phone and computer are on the **same Wi-Fi network**
2. In WeChat Developer Tools, click **Debug on Device**
3. Scan the QR code with your phone
4. If connection fails, check:
   - Computer firewall allows port `8080`
   - `config.js` has the correct LAN IP (not `localhost`)
   - Java backend is running

## Configuration

### Switching the LLM model

Edit `backend-ai/core/config.py`:

```python
llm = ChatOpenAI(
    model="deepseek-v4-flash",   # change model here
    api_key=API_KEY,
    base_url=BASE_URL,
    temperature=0.3               # 0.0 = deterministic, 1.0 = creative
)
```

Available DeepSeek models:
| Model | Speed | Cost | Recommended for |
|-------|:-----:|:----:|-----------------|
| `deepseek-v4-flash` | Fast | Very low | Development, demo (default) |
| `deepseek-v4` | Medium | Low | Better quality answers |

### OCR engine

`ocrmac` (macOS Vision) is used by default. To switch to Tesseract on Linux:

```bash
# Install Tesseract with Chinese support
sudo apt install tesseract-ocr tesseract-ocr-chi-sim

# Install Python wrapper
pip install pytesseract
```

Then modify `backend-ai/services/ocr.py` to use `pytesseract` instead of `ocrmac`.

### Embedding model

The default model is `BAAI/bge-small-zh-v1.5` (Chinese medical text optimized, ~90MB). It runs locally on CPU — no API calls needed. To change:

```python
# backend-ai/core/config.py
embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",  # change model here
    model_kwargs={"local_files_only": True, "device": "cpu"}
)
```

> Change `local_files_only` to `False` on first use to download from HuggingFace.

### Risk keywords

Edit `risk_keywords.json` to add or remove trigger words:

```json
{
  "keywords": ["overdose", "poisoning", "allergy", "contraindication", "side effect", "..."]
}
```

When a configured keyword appears in the user's question, the system records a risk event and can send an email alert.

### Admin dashboard security

The admin dashboard restricts access by IP whitelist. Configure in `backend-java/src/main/resources/application.properties`:

```properties
admin.security.enabled=true
admin.security.ip-whitelist=127.0.0.1,::1
```

Add your IP to the whitelist if accessing remotely.

### Embedding model first-run setup

The embedding model is cached locally after first download. If you need to force a re-download:

```bash
cd backend-ai
source venv/bin/activate
python -c "from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='BAAI/bge-small-zh-v1.5')"
```

## API Endpoints

### Python AI Service (`:8001`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/internal/ocr` | Internal OCR endpoint for image/PDF/Word extraction |
| `POST` | `/internal/chat` | Internal RAG question-answering endpoint |
| `POST` | `/internal/transcribe` | Internal speech-to-text endpoint (Whisper via Groq) |
| `POST` | `/internal/analyze_text` | Internal manual-text analysis endpoint |
| `GET` | `/internal/tts` | Internal text-to-speech endpoint (edge-tts) |

### Java Backend (`:8080`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/medicine/health` | Health check |
| `POST` | `/api/medicine/upload` | Upload and recognize a medicine document |
| `POST` | `/api/medicine/chat` | Proxy to AI service chat |
| `POST` | `/api/medicine/transcribe` | Transcribe audio |
| `POST` | `/api/medicine/analyze_text` | Analyze manually entered text |
| `GET` | `/api/medicine/tts` | Generate speech audio |
| `GET` | `/api/medicine/search` | Search stored medicines |
| `GET` | `/api/medicine/chat-logs` | Chat log history (admin) |
| `GET` | `/api/medicine/chat-logs/risky` | Risk-flagged chat logs |
| `GET` | `/api/medicine/analytics/top-medicines` | Most consulted medicines |

## Testing

```bash
# Python unit tests (17 tests, ~0.2s)
cd backend-ai
source venv/bin/activate
python -m pytest tests/ -v

# Java unit tests (6 tests)
cd backend-java
mvn test
```

### Test coverage

| Module | Tests | Covers |
|--------|:-----:|--------|
| `check_risk_keywords` | 6 | Hit, cache, expiry, empty input |
| `smart_rag_search` | 4 | Short text, long text, error fallback, edge cases |
| `correct_medical_terms` | 7 | Hallucination filter, blacklist, LLM correction, error fallback |
| `MedicineController` | 6 | REST endpoint MockMvc tests |

## Project Structure

```
MedVision-RAG/
├── frontend/                  # Vue 3 CDN single-page web app
│   └── index.html             # Complete frontend (848 lines)
├── frontend-wechat/           # WeChat Mini Program
│   ├── pages/index/           # Main page (WXML + JS + WXSS)
│   ├── app.js                 # App entry
│   └── config.js              # API endpoint configuration
├── backend-java/              # Spring Boot business backend
│   ├── src/main/java/com/medvision/
│   │   ├── controller/        # REST endpoints
│   │   ├── service/           # Business logic
│   │   ├── entity/            # JPA entities (Medicine, ChatLog, AdminUser)
│   │   ├── repository/        # Spring Data JPA repositories
│   │   └── config/            # Security, CORS, IP whitelist, data init
│   ├── src/test/              # MockMvc tests
│   └── pom.xml                # Maven dependencies
├── backend-ai/                # FastAPI AI service
│   ├── main.py                # Route entry (~250 lines)
│   ├── core/
│   │   ├── config.py          # Global singletons (LLM, embedding, Groq client)
│   │   ├── logging_config.py  # Structured logging + trace middleware
│   │   └── security.py        # Internal token verification
│   ├── services/
│   │   ├── ocr.py             # OCR (ocrmac + Tesseract fallback)
│   │   ├── asr.py             # Speech recognition (Groq Whisper)
│   │   ├── rag.py             # Adaptive RAG (context stuffing + vector search)
│   │   ├── tts.py             # Text-to-speech (edge-tts)
│   │   ├── risk.py            # Risk keyword detection + TTL cache
│   │   ├── email.py           # Risk alert email (async thread pool)
│   │   ├── intent.py          # Intent analysis (current vs historical drug)
│   │   ├── search.py          # Drug history search
│   │   └── chat_model.py      # Chat model switching
│   ├── models/
│   │   └── schemas.py         # Pydantic request models
│   └── tests/                 # pytest unit tests
├── admin_dashboard.py         # Streamlit admin dashboard
├── risk_keywords.json         # Risk keyword dictionary
├── sql/
│   └── init.sql               # Database initialization script
├── Package-Insert_Test/       # Sample drug inserts for testing
├── .env.example               # Environment variable template
├── .gitignore                 # Git ignore rules
├── start_all.sh               # One-command start all services
└── stop_all.sh                # One-command stop all services
```

## FAQ

### Installation & Startup

**`No module named 'ocrmac'`**

`ocrmac` uses the macOS Vision framework and only works on macOS. For Linux, install Tesseract:

```bash
sudo apt install tesseract-ocr tesseract-ocr-chi-sim
pip install pytesseract
```

Then modify `backend-ai/services/ocr.py` to use `pytesseract`.

**`Connection refused` when starting Java backend**

MySQL is not running or the password is wrong.

```bash
# Check MySQL status
mysql -u root -p -e "SELECT 1"

# Verify .env password matches your MySQL root password
cat .env | grep MYSQL_PASSWORD
```

**`torchaudio` warning on Python startup**

This is a non-fatal warning about VAD (Voice Activity Detection). The system falls back to no-VAD mode and works fine. To fix: `pip install torchaudio`.

**Maven download is slow**

Add a mirror to `~/.m2/settings.xml`:

```xml
<mirrors>
  <mirror>
    <id>aliyun</id>
    <mirrorOf>central</mirrorOf>
    <url>https://maven.aliyun.com/repository/central</url>
  </mirror>
</mirrors>
```

### Usage

**White screen in browser**

Open DevTools (F12) → Console tab. Common causes:
- AI service not started → check port `8001`
- Java backend not started → check port `8080`
- CORS error → make sure you access via `localhost:5174`, not `file://`

**Mini program can't connect to backend**

1. Verify phone and computer are on the **same Wi-Fi network**
2. Check `config.js` has your LAN IP (not `localhost` or `127.0.0.1`)
3. Check your computer's firewall allows incoming connections on port `8080`
4. Try `curl http://YOUR_LAN_IP:8080/api/medicine/health` from your phone's browser

**Speech recognition not working (web)**

Browsers require HTTPS or `localhost` for microphone access. Make sure you access the page via `http://localhost:5174`, not a LAN IP.

**Speech recognition not working (Mini Program)**

Check that `GROQ_API_KEY` is set in `.env`. Restart the Python AI service after changing `.env`.

**OCR returns "unknown drug" or garbled text**

- Make sure the photo is clear and well-lit
- The drug name should be visible in the image
- For PDFs, check if the file is a scanned image (not searchable text) — the system will auto-detect and use image OCR

### Database

**How to reset the database**

```bash
mysql -u root -p -e "DROP DATABASE IF EXISTS medvision;"
mysql -u root -p < sql/init.sql
```

Then restart the Java backend to recreate the default admin account.

**How to change the admin password**

Use the Admin Dashboard (http://localhost:8502) after logging in, or update directly in MySQL:

```sql
USE medvision;
UPDATE admin_users SET password_hash = '$2a$10$...' WHERE username = 'admin';
```

Generate a BCrypt hash using any online tool or Python:

```python
from passlib.hash import bcrypt
print(bcrypt.hash("your_new_password"))
```

## License

No license file is currently included in this repository. Add an explicit license before distributing or reusing the project outside its intended scope.
