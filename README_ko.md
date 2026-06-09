<p align="center">
  <img src="assets/logo.png" alt="MedVision-RAG Logo" width="200">
</p>

<h1 align="center">MedVision-RAG</h1>

<p align="center">
  <strong>음성 인터랙션 기반 AI 복약 보조 시스템</strong><br>
  의약품 설명서를 촬영하면 RAG + 음성으로 즉시 답변을 제공합니다.
</p>

<p align="center">
    <a href="README.md">English</a> · <a href="README_CN.md">简体中文</a> · <a href="README_TW.md">繁體中文</a> · <a href="README_ja.md">日本語</a> · <a href="README_es.md">Español</a> · <a href="README_pt-BR.md">Português</a> · <a href="README_ru.md">Русский</a> · <a href="README_fr.md">Français</a> · <a href="README_de.md">Deutsch</a>
</p>

---

## 개요

MedVision-RAG는 시각장애인과 고령 사용자가 의약품 정보를 쉽게 이해할 수 있도록 돕는 시스템입니다. 의약품 포장지를 카메라로 촬영하거나 PDF/Word 문서를 업로드하면 다음과 같이 동작합니다:

1. **텍스트 추출** — OCR(macOS Vision / Tesseract 폴백) 수행
2. **텍스트 정제** — Unstructured.io 파이프라인으로 공백, 깨진 문단, 글머리표 정리
3. **지식 베이스 구축** — 텍스트를 벡터화하여 ChromaDB에 저장
4. **질의응답** — 적응형 RAG: 짧은 텍스트는 직접 컨텍스트 주입, 긴 텍스트는 벡터 유사도 검색
5. **음성 출력** — edge-tts로 답변을 음성으로 읽어줌

**웹 브라우저**, **위챗 미니 프로그램**, 그리고 채팅 로그와 분석을 모니터링하는 **관리자 대시보드**를 지원합니다.

## 주요 기능

### 다중 포맷 OCR
- **사진**: 의약품 포장지, 박스, 블리스터 팩 — 카메라로 직접 촬영
- **PDF**: 텍스트 기반 및 스캔 문서 자동 감지 후 이미지 렌더링하여 OCR 수행
- **Word**: 텍스트 및 표 추출; 텍스트가 부족하면 내장 이미지 OCR로 폴백
- **HEIC/HEIF**: iPhone 사진은 OCR 전 자동으로 JPEG 변환

### 적응형 RAG 엔진
- **짧은 텍스트** (< 1500자): 컨텍스트 스터핑 — 전체 문서를 LLM 프롬프트에 주입
- **긴 텍스트** (>= 1500자): 벡터 검색 — 청크 단위로 분할하여 ChromaDB에 저장하고, 상위 K개 관련 구간 검색
- **교차 약품 전환**: 사용자가 다른 약품명을 언급하면 시스템이 자동으로 컨텍스트 전환

### 음성 인터랙션
- **웹**: 브라우저 내장 Speech Recognition API (제로 레이턴시, API 비용 없음)
- **미니 프로그램**: Groq Whisper Large-V3로 음성 → 텍스트, edge-tts로 텍스트 → 음성
- **의료 용어 교정**: LLM이 ASR 출력을 후처리하여 오인식된 약품명 수정
- **중단 가능한 재생**: 음성 버튼을 누르면 진행 중인 TTS를 즉시 중단

### 위험 모니터링
- **키워드 감지**: `risk_keywords.json`에서 설정 가능한 위험 키워드
- **채팅 로그 감사**: 모든 대화를 MySQL에 저장하여 검토 가능
- **이메일 알림**: 위험 키워드 감지 시 자동 이메일 발송 (설정 가능)
- **관리자 대시보드**: Streamlit 기반 실시간 모니터링, IP 화이트리스트 보호

### 접근성
- 고대비 UI (WCAG AA 준수)
- 큰 터치 영역 (48px 이상)
- 시각장애인을 위한 완전 음성 기반 워크플로우
- 중국어/영어 언어 전환 — AI 응답 및 TTS 언어 동기화

## 시스템 아키텍처

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Web Front  │────▶│  Java Backend    │────▶│  Python AI       │
│  :5174      │     │  Spring Boot     │     │  FastAPI          │
│  Vue 3      │     │  :8080           │     │  :8001            │
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

## 시스템 요구사항

| 의존성 | 버전 | 비고 |
|:-------|:----:|------|
| Python | 3.10+ | AI 서비스 런타임 |
| Java | 17+ | 비즈니스 백엔드 런타임 |
| Maven | 3.8+ | Java 빌드 도구 |
| MySQL | 8.0+ | 관계형 데이터 저장소 |
| macOS (권장) | 13+ | `ocrmac`이 Apple Vision 프레임워크를 사용하여 OCR 수행 |

> **Linux**: 지원되지만 OCR에 [Tesseract](https://github.com/tesseract-ocr/tesseract)가 필요합니다. `apt install tesseract-ocr tesseract-ocr-chi-sim`으로 설치한 후 `backend-ai/services/ocr.py`를 수정하세요.

## API 키

**DeepSeek API Key**가 필수이며, **Groq API Key**는 선택사항입니다 (위챗 미니 프로그램 음성 인식용).

<details>
<summary><strong>DeepSeek API Key 발급 방법 (필수)</strong></summary>

DeepSeek는 질의응답에 사용되는 LLM을 제공합니다.

1. [platform.deepseek.com](https://platform.deepseek.com/)에 접속
2. 회원가입 또는 로그인
3. 왼쪽 사이드바에서 **API Keys**로 이동
4. **Create API Key** 클릭 후 이름 입력 (예: "MedVision")
5. 키를 즉시 복사 (`sk-`로 시작하며 다시 확인할 수 없음)

**비용**: 기본 모델 `deepseek-v4-flash`는 매우 저렴합니다. 하루 종일 개발 테스트해도 보통 $0.01 미만입니다.

</details>

<details>
<summary><strong>Groq API Key 발급 방법 (선택 — 미니 프로그램 전용)</strong></summary>

Groq는 LPU 하드웨어에서 Whisper Large-V3를 통해 빠른 음성 → 텍스트 변환을 제공합니다.

1. [console.groq.com](https://console.groq.com/)에 접속
2. GitHub 또는 Google 계정으로 가입
3. 왼쪽 사이드바에서 **API Keys**로 이동
4. **Create API Key** 클릭
5. 키 복사 (`gsk-`로 시작)

**비용**: 무료 플랜에 넉넉한 Whisper 사용량이 포함되어 있습니다. 웹 프론트엔드는 브라우저 내장 음성 API를 사용하므로 Groq 크레딧을 소비하지 않습니다 — 위챗 미니 프로그램만 Groq를 사용합니다.

</details>

## 설치 방법

### 1. 클론

```bash
git clone https://github.com/Ha1baraA11/MedVision_RAG.git
cd MedVision_RAG
```

### 2. 환경 설정

```bash
cp .env.example .env
```

텍스트 편집기로 `.env`를 열어 필요한 값을 입력합니다:

```bash
# macOS
open -e .env

# VS Code
code .env
```

| 변수 | 필수 | 설명 |
|------|:----:|------|
| `MYSQL_PASSWORD` | **예** | MySQL root 비밀번호 |
| `DEEPSEEK_API_KEY` | **예** | [platform.deepseek.com](https://platform.deepseek.com/)에서 발급 |
| `DEEPSEEK_BASE_URL` | 아니오 | 기본값: `https://api.deepseek.com` |
| `GROQ_API_KEY` | 미니 프로그램용 | [console.groq.com](https://console.groq.com/)에서 발급 |
| `SMTP_SERVER` | 아니오 | 위험 알림용 SMTP 서버 (예: `smtp.qq.com`) |
| `SMTP_PORT` | 아니오 | SMTP 포트 (QQ 메일: `465`) |
| `SMTP_USER` | 아니오 | 발신자 이메일 주소 |
| `SMTP_PASSWORD` | 아니오 | SMTP 인증 코드 (이메일 비밀번호와 다름) |
| `SMTP_RECEIVER` | 아니오 | 수신자 이메일 주소 |
| `INTERNAL_TOKEN` | 아니오 | Java ↔ Python 서비스 간 인증 토큰 |

> **참고**: `MYSQL_PASSWORD`는 시스템 시작에 반드시 필요한 유일한 자격 증명입니다. 나머지는 안전한 기본값이 설정되어 있거나 점진적 성능 저하로 처리됩니다.

<details>
<summary><strong>QQ 메일 SMTP 인증 코드 발급 방법</strong></summary>

1. [mail.qq.com](https://mail.qq.com/) 로그인 → 설정 → 계정
2. **POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV 서비스** 항목 찾기
3. **IMAP/SMTP 서비스** 활성화
4. SMS 인증 절차를 거쳐 **인증 코드** 발급
5. 이 코드(QQ 비밀번호가 아님)를 `SMTP_PASSWORD`로 사용

</details>

### 3. Python 환경 설정

```bash
cd backend-ai

# 가상 환경 생성
python3 -m venv venv

# 활성화
source venv/bin/activate

# 의존성 설치 (최초 실행 시에만, 약 2분 소요)
pip install -r requirements.txt
```

최초 실행 시 HuggingFace에서 `bge-small-zh-v1.5` 임베딩 모델(~90MB)을 다운로드합니다.

### 4. Java 환경 설정

```bash
cd backend-java

# 의존성 다운로드 및 컴파일 (최초 실행 시에만, 약 3분 소요)
mvn clean install -DskipTests
```

### 5. 데이터베이스 초기화

```bash
mysql -u root -p < sql/init.sql
```

생성되는 항목:
- 데이터베이스 `medvision` (UTF8MB4)
- 테이블 `medicines` — 의약품 정보 및 전문 텍스트
- 테이블 `chat_logs` — 대화 이력 및 분석 데이터
- 테이블 `admin_users` — 관리자 계정

기본 관리자 계정(`admin` / `admin`)은 Java 백엔드가 처음 시작될 때 자동 생성됩니다.

> **대안**: 이 단계를 건너뛰면 Spring Boot의 `hibernate.ddl-auto=update` 설정에 따라 테이블이 자동 생성됩니다. SQL 스크립트는 명시적인 스키마 관리 및 프로덕션 배포용으로 제공됩니다.

## 사용 방법

### 빠른 시작 (모든 서비스 한 번에 실행)

```bash
./start_all.sh
```

이 스크립트는 의존성 순서에 따라 모든 서비스를 시작하고, 각 서비스가 준비될 때까지 대기한 후 상태를 출력합니다. 로그는 `backend-ai/service.log`, `backend-java/backend.log`, `dashboard.log`에 기록됩니다.

### 수동 시작 (터미널 3개 분리)

**터미널 1 — Python AI 서비스** (가장 느리므로 먼저 시작)

```bash
cd backend-ai
source venv/bin/activate
python main.py
```

다음 메시지 확인: `Uvicorn running on http://0.0.0.0:8001`

> 최초 시작 시 임베딩 모델(`bge-small-zh-v1.5`)이 다운로드되어 캐시됩니다. 이후 시작은 약 3초 소요됩니다.

**터미널 2 — Java 백엔드**

```bash
cd backend-java
mvn spring-boot:run
```

다음 메시지 확인: `Started MedVisionApplication in X.XXX seconds`

> Maven이 최초 실행 시 의존성을 다운로드합니다. 백엔드가 데이터베이스 테이블과 기본 관리자 계정을 자동 생성합니다.

**터미널 3 — 웹 프론트엔드**

```bash
cd frontend
python3 -m http.server 5174
```

브라우저에서 http://localhost:5174 접속.

**선택 — 관리자 대시보드**

```bash
streamlit run admin_dashboard.py --server.port 8502
```

http://localhost:8502 접속. 로그인: `admin` / `admin`.

### 모든 서비스 중지

```bash
./stop_all.sh
```

또는 수동으로:

```bash
lsof -t -i:5174 -i:8080 -i:8001 -i:8502 | xargs kill -9
```

## 위챗 미니 프로그램

### 설정

1. [WeChat Developer Tools](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html) 다운로드 및 설치
2. 도구를 열고 **Import Project** 클릭
3. `frontend-wechat/` 디렉토리 선택
4. **Test AppID** 또는 게스트 모드 선택
5. `frontend-wechat/config.js` 편집:

```js
const API_CANDIDATES = [
  'http://192.168.x.x:8080',  // 컴퓨터의 LAN IP로 변경
];
```

### LAN IP 확인

```bash
# macOS
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr "IPv4"
```

### 실기기 디버깅

1. 스마트폰과 컴퓨터가 **동일한 Wi-Fi 네트워크**에 연결되어 있는지 확인
2. WeChat Developer Tools에서 **Debug on Device** 클릭
3. 스마트폰으로 QR 코드 스캔
4. 연결 실패 시 확인 사항:
   - 컴퓨터 방화벽이 포트 `8080`을 허용하는지 확인
   - `config.js`에 올바른 LAN IP가 설정되어 있는지 확인 (`localhost`가 아닌)
   - Java 백엔드가 실행 중인지 확인

## 설정

### LLM 모델 변경

`backend-ai/core/config.py` 편집:

```python
llm = ChatOpenAI(
    model="deepseek-v4-flash",   # 여기서 모델 변경
    api_key=API_KEY,
    base_url=BASE_URL,
    temperature=0.3               # 0.0 = 결정적, 1.0 = 창의적
)
```

사용 가능한 DeepSeek 모델:
| 모델 | 속도 | 비용 | 용도 |
|------|:----:|:----:|------|
| `deepseek-v4-flash` | 빠름 | 매우 저렴 | 개발, 데모 (기본값) |
| `deepseek-v4` | 보통 | 저렴 | 더 나은 품질의 답변 |

### OCR 엔진

기본값은 `ocrmac`(macOS Vision)입니다. Linux에서 Tesseract로 전환하려면:

```bash
# 중국어 지원 Tesseract 설치
sudo apt install tesseract-ocr tesseract-ocr-chi-sim

# Python 래퍼 설치
pip install pytesseract
```

그런 다음 `backend-ai/services/ocr.py`에서 `ocrmac` 대신 `pytesseract`를 사용하도록 수정합니다.

### 임베딩 모델

기본 모델은 `BAAI/bge-small-zh-v1.5` (중국어 의료 텍스트 최적화, ~90MB)입니다. CPU에서 로컬 실행 — API 호출 불필요. 변경하려면:

```python
# backend-ai/core/config.py
embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",  # 여기서 모델 변경
    model_kwargs={"local_files_only": True, "device": "cpu"}
)
```

> 최초 사용 시 HuggingFace에서 다운로드하려면 `local_files_only`를 `False`로 변경하세요.

### 위험 키워드

`risk_keywords.json`을 편집하여 트리거 단어를 추가하거나 제거합니다:

```json
{
  "keywords": ["过量", "中毒", "过敏", "禁忌", "副作用", "..."]
}
```

사용자의 질문이나 AI 응답에 키워드가 포함되면 시스템이 이벤트를 기록하고 (설정된 경우) 이메일 알림을 발송합니다.

### 관리자 대시보드 보안

관리자 대시보드는 IP 화이트리스트로 접근을 제한합니다. `backend-java/src/main/resources/application.properties`에서 설정:

```properties
admin.security.enabled=true
admin.security.ip-whitelist=127.0.0.1,::1
```

원격 접속 시 화이트리스트에 IP를 추가하세요.

### 임베딩 모델 최초 실행 설정

임베딩 모델은 최초 다운로드 후 로컬에 캐시됩니다. 강제로 다시 다운로드하려면:

```bash
cd backend-ai
source venv/bin/activate
python -c "from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='BAAI/bge-small-zh-v1.5')"
```

## API 엔드포인트

### Python AI 서비스 (`:8001`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/health` | 헬스 체크 |
| `POST` | `/ocr` | 이미지/PDF/Word → 텍스트 추출 |
| `POST` | `/chat` | RAG 질의응답 |
| `POST` | `/transcribe` | 음성 → 텍스트 (Groq Whisper) |
| `POST` | `/analyze` | 수동 텍스트 분석 |
| `GET` | `/tts` | 텍스트 → 음성 (edge-tts) |
| `GET` | `/search` | 의약품 이력 검색 |

### Java 백엔드 (`:8080`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/medicine/health` | 헬스 체크 |
| `POST` | `/api/medicine/recognize` | 의약품 설명서 업로드 및 인식 |
| `POST` | `/api/medicine/chat` | AI 서비스 채팅 프록시 |
| `GET` | `/api/medicine/list` | 저장된 의약품 목록 조회 |
| `GET` | `/api/medicine/chat-logs` | 채팅 로그 이력 (관리자) |
| `GET` | `/api/medicine/analytics` | 사용 분석 (관리자) |
| `POST` | `/api/medicine/admin/login` | 관리자 로그인 |

## 테스트

```bash
# Python 단위 테스트 (17개, 약 0.2초)
cd backend-ai
source venv/bin/activate
python -m pytest tests/ -v

# Java 단위 테스트 (6개)
cd backend-java
mvn test
```

### 테스트 커버리지

| 모듈 | 테스트 수 | 커버리지 |
|------|:---------:|----------|
| `check_risk_keywords` | 6 | 히트, 캐시, 만료, 빈 입력 |
| `smart_rag_search` | 4 | 짧은 텍스트, 긴 텍스트, 오류 폴백, 엣지 케이스 |
| `correct_medical_terms` | 7 | 환각 필터, 블랙리스트, LLM 교정, 오류 폴백 |
| `MedicineController` | 6 | REST 엔드포인트 MockMvc 테스트 |

## 프로젝트 구조

```
MedVision-RAG/
├── frontend/                  # Vue 3 단일 파일 웹 앱
│   └── index.html             # 완전한 프론트엔드 (848줄)
├── frontend-wechat/           # 위챗 미니 프로그램
│   ├── pages/index/           # 메인 페이지 (WXML + JS + WXSS)
│   ├── app.js                 # 앱 진입점
│   └── config.js              # API 엔드포인트 설정
├── backend-java/              # Spring Boot 비즈니스 백엔드
│   ├── src/main/java/com/medvision/
│   │   ├── controller/        # REST 엔드포인트
│   │   ├── service/           # 비즈니스 로직
│   │   ├── entity/            # JPA 엔티티 (Medicine, ChatLog, AdminUser)
│   │   ├── repository/        # Spring Data JPA 리포지토리
│   │   └── config/            # 보안, CORS, IP 화이트리스트, 데이터 초기화
│   ├── src/test/              # MockMvc 테스트
│   └── pom.xml                # Maven 의존성
├── backend-ai/                # FastAPI AI 서비스
│   ├── main.py                # 라우트 진입점 (~250줄)
│   ├── core/
│   │   ├── config.py          # 전역 싱글턴 (LLM, 임베딩, Groq 클라이언트)
│   │   ├── logging_config.py  # 구조화된 로깅 + 추적 미들웨어
│   │   └── security.py        # 내부 토큰 검증
│   ├── services/
│   │   ├── ocr.py             # OCR (ocrmac + Tesseract 폴백)
│   │   ├── asr.py             # 음성 인식 (Groq Whisper)
│   │   ├── rag.py             # 적응형 RAG (컨텍스트 스터핑 + 벡터 검색)
│   │   ├── tts.py             # 텍스트 → 음성 (edge-tts)
│   │   ├── risk.py            # 위험 키워드 감지 + TTL 캐시
│   │   ├── email.py           # 위험 알림 이메일 (비동기 스레드 풀)
│   │   ├── intent.py          # 의도 분석 (현재 vs 과거 약품)
│   │   ├── search.py          # 의약품 이력 검색
│   │   └── chat_model.py      # 채팅 모델 전환
│   ├── models/
│   │   └── schemas.py         # Pydantic 요청 모델
│   └── tests/                 # pytest 단위 테스트
├── admin_dashboard.py         # Streamlit 관리자 대시보드
├── risk_keywords.json         # 위험 키워드 사전
├── sql/
│   └── init.sql               # 데이터베이스 초기화 스크립트
├── Package-Insert_Test/       # 테스트용 샘플 의약품 설명서
├── .env.example               # 환경 변수 템플릿
├── .gitignore                 # Git 무시 규칙
├── start_all.sh               # 모든 서비스 원커맨드 시작
└── stop_all.sh                # 모든 서비스 원커맨드 중지
```

## FAQ

### 설치 및 시작

**`No module named 'ocrmac'`**

`ocrmac`는 macOS Vision 프레임워크를 사용하며 macOS에서만 동작합니다. Linux에서는 Tesseract를 설치하세요:

```bash
sudo apt install tesseract-ocr tesseract-ocr-chi-sim
pip install pytesseract
```

그런 다음 `backend-ai/services/ocr.py`에서 `pytesseract`를 사용하도록 수정합니다.

**Java 백엔드 시작 시 `Connection refused`**

MySQL이 실행 중이 아니거나 비밀번호가 잘못되었습니다.

```bash
# MySQL 상태 확인
mysql -u root -p -e "SELECT 1"

# .env 비밀번호가 MySQL root 비밀번호와 일치하는지 확인
cat .env | grep MYSQL_PASSWORD
```

**Python 시작 시 `torchaudio` 경고**

VAD(Voice Activity Detection) 관련 비치명적 경고입니다. 시스템은 VAD 모드 없이 폴백되어 정상 동작합니다. 해결하려면: `pip install torchaudio`.

**Maven 다운로드가 느린 경우**

`~/.m2/settings.xml`에 미러를 추가합니다:

```xml
<mirrors>
  <mirror>
    <id>aliyun</id>
    <mirrorOf>central</mirrorOf>
    <url>https://maven.aliyun.com/repository/central</url>
  </mirror>
</mirrors>
```

### 사용 중 문제 해결

**브라우저에 빈 화면 표시**

개발자 도구(F12) → Console 탭 확인. 흔한 원인:
- AI 서비스가 시작되지 않음 → 포트 `8001` 확인
- Java 백엔드가 시작되지 않음 → 포트 `8080` 확인
- CORS 오류 → `localhost:5174`로 접속했는지 확인, `file://`로 접속하지 말 것

**미니 프로그램이 백엔드에 연결되지 않음**

1. 스마트폰과 컴퓨터가 **동일한 Wi-Fi 네트워크**에 있는지 확인
2. `config.js`에 LAN IP가 설정되어 있는지 확인 (`localhost` 또는 `127.0.0.1`이 아닌)
3. 컴퓨터 방화벽이 포트 `8080`의 인바운드 연결을 허용하는지 확인
4. 스마트폰 브라우저에서 `http://YOUR_LAN_IP:8080/api/medicine/health` 접속 시도

**음성 인식이 작동하지 않음 (웹)**

브라우저는 마이크 접근에 HTTPS 또는 `localhost`를 요구합니다. `http://localhost:5174`로 접속했는지 확인하세요. LAN IP로는 접속할 수 없습니다.

**음성 인식이 작동하지 않음 (미니 프로그램)**

`.env`에 `GROQ_API_KEY`가 설정되어 있는지 확인하세요. `.env` 변경 후 Python AI 서비스를 재시작해야 합니다.

**OCR이 "알 수 없는 약품"을 반환하거나 텍스트가 깨짐**

- 사진이 선명하고 조명이 밝은지 확인
- 약품명이 이미지에 보여야 함
- PDF의 경우, 파일이 스캔 이미지(검색 불가능한 텍스트)인지 확인 — 시스템이 자동 감지하여 이미지 OCR을 사용합니다

### 데이터베이스

**데이터베이스 초기화 방법**

```bash
mysql -u root -p -e "DROP DATABASE IF EXISTS medvision;"
mysql -u root -p < sql/init.sql
```

그런 다음 Java 백엔드를 재시작하여 기본 관리자 계정을 다시 생성합니다.

**관리자 비밀번호 변경 방법**

관리자 대시보드(http://localhost:8502)에서 로그인 후 변경하거나, MySQL에서 직접 업데이트:

```sql
USE medvision;
UPDATE admin_users SET password_hash = '$2a$10$...' WHERE username = 'admin';
```

BCrypt 해시는 온라인 도구 또는 Python으로 생성:

```python
from passlib.hash import bcrypt
print(bcrypt.hash("your_new_password"))
```

## 라이선스

MIT
