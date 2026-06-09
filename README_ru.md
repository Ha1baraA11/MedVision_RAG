<p align="center">
  <img src="assets/logo.png" alt="MedVision-RAG Logo" width="200">
</p>

<h1 align="center">MedVision-RAG</h1>

<p align="center">
  <strong>ИИ-ассистент по лекарствам с голосовым управлением</strong><br>
  Сфотографируйте инструкцию к препарату — получите ответ через RAG и голосовой интерфейс.
</p>

<p align="center">
  <a href="README.md">English</a> · <a href="README_CN.md">简体中文</a> · <a href="README_TW.md">繁體中文</a> · <a href="README_ja.md">日本語</a> · <a href="README_ko.md">한국어</a> · <a href="README_es.md">Español</a> · <a href="README_pt-BR.md">Português</a> · <a href="README_fr.md">Français</a> · <a href="README_de.md">Deutsch</a>
</p>

---

## Что делает проект

MedVision-RAG помогает незрячим и пожилым людям разобраться в лекарствах. Направьте камеру на упаковку препарата или загрузите PDF/Word-документ — система:

1. **Извлекает текст** через OCR (macOS Vision / Tesseract как запасной вариант)
2. **Очищает текст** с помощью конвейера Unstructured.io (пробелы, разорванные абзацы, маркированные списки)
3. **Создаёт базу знаний**, векторизуя текст в ChromaDB
4. **Отвечает на вопросы** с помощью адаптивного RAG — для коротких текстов используется прямая вставка контекста, для длинных — векторный поиск по сходству
5. **Озвучивает ответ** через edge-tts

Система поддерживает **веб-браузер**, **мини-программу WeChat** и **панель администратора** для мониторинга журналов чатов и аналитики.

## Возможности

### Многоформатный OCR
- **Фотографии**: упаковки, коробки, блистеры — напрямую через камеру
- **PDF**: как текстовые, так и отсканированные (автоопределение и рендеринг в изображение для OCR)
- **Word**: извлечение текста и таблиц; если текста недостаточно — OCR встроенных изображений
- **HEIC/HEIF**: фотографии с iPhone автоматически конвертируются в JPEG перед OCR

### Адаптивный движок RAG
- **Короткий текст** (< 1500 символов): Context Stuffing — полный документ вставляется в промпт LLM
- **Длинный текст** (>= 1500 символов): векторный поиск — текст разбивается на фрагменты, сохраняется в ChromaDB, извлекаются наиболее релевантные отрывки (top-K)
- **Переключение между препаратами**: когда пользователь упоминает другое лекарство, система автоматически переключает контекст

### Голосовое взаимодействие
- **Веб**: нативный Speech Recognition API браузера (нулевая задержка, без затрат на API)
- **Мини-программа**: Groq Whisper Large-V3 для распознавания речи, edge-tts для синтеза речи
- **Коррекция медицинских терминов**: LLM постобрабатывает результат ASR для исправления неверно распознанных названий лекарств
- **Прерываемое воспроизведение**: нажмите кнопку озвучки, чтобы немедленно остановить текущий TTS

### Мониторинг рисков
- **Обнаружение ключевых слов**: настраиваемые ключевые слова риска в `risk_keywords.json`
- **Аудит журналов**: все диалоги сохраняются в MySQL для проверки
- **Оповещения по email**: автоматическое уведомление при срабатывании ключевых слов (настраивается)
- **Панель администратора**: мониторинг в реальном времени через Streamlit с защитой по IP-адресам

### Доступность
- Высококонтрастный интерфейс (соответствие WCAG AA)
- Увеличенные области нажатия (48px+)
- Полностью голосовой рабочий процесс для незрячих пользователей
- Переключение китайский/английский с синхронизацией языка ответа ИИ и TTS

## Архитектура

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

## Зависимости

| Зависимость | Версия | Примечания |
|:-----------|:-------:|------------|
| Python | 3.10+ | Среда выполнения ИИ-сервиса |
| Java | 17+ | Среда выполнения бизнес-бэкенда |
| Maven | 3.8+ | Сборщик Java |
| MySQL | 8.0+ | Реляционное хранилище данных |
| macOS (рекомендуется) | 13+ | `ocrmac` использует фреймворк Apple Vision для OCR |

> **Linux**: поддерживается, но требуется [Tesseract](https://github.com/tesseract-ocr/tesseract) для OCR. Установка: `apt install tesseract-ocr tesseract-ocr-chi-sim`, затем измените `backend-ai/services/ocr.py`.

## API-ключи

Необходим **DeepSeek API Key** (обязательно) и опционально **Groq API Key** (для распознавания речи в мини-программе WeChat).

<details>
<summary><strong>Как получить DeepSeek API Key (обязательно)</strong></summary>

DeepSeek предоставляет LLM для ответов на вопросы.

1. Перейдите на [platform.deepseek.com](https://platform.deepseek.com/)
2. Зарегистрируйтесь или войдите
3. Перейдите в раздел **API Keys** в боковом меню
4. Нажмите **Create API Key**, задайте имя (например "MedVision")
5. Скопируйте ключ немедленно (начинается с `sk-`, повторно не отображается)

**Стоимость**: модель по умолчанию `deepseek-v4-flash` крайне дешёвая. Полный день разработки и тестирования обычно стоит менее $0.01.

</details>

<details>
<summary><strong>Как получить Groq API Key (опционально — только для мини-программы)</strong></summary>

Groq обеспечивает быстрое распознавание речи через Whisper Large-V3 на аппаратуре LPU.

1. Перейдите на [console.groq.com](https://console.groq.com/)
2. Зарегистрируйтесь через GitHub или Google
3. Перейдите в раздел **API Keys** в боковом меню
4. Нажмите **Create API Key**
5. Скопируйте ключ (начинается с `gsk-`)

**Стоимость**: бесплатный тариф включает щедрый лимит на Whisper. Веб-интерфейс использует встроенный Speech API браузера и **не расходует** кредиты Groq — только мини-программа WeChat использует Groq.

</details>

## Установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/Ha1baraA11/MedVision_RAG.git
cd MedVision_RAG
```

### 2. Настройка окружения

```bash
cp .env.example .env
```

Откройте `.env` в любом текстовом редакторе и заполните значения:

```bash
# macOS
open -e .env

# VS Code
code .env
```

| Переменная | Обязательна | Описание |
|------------|:-----------:|----------|
| `MYSQL_PASSWORD` | **Да** | Пароль root-пользователя MySQL |
| `DEEPSEEK_API_KEY` | **Да** | Получить на [platform.deepseek.com](https://platform.deepseek.com/) |
| `DEEPSEEK_BASE_URL` | Нет | По умолчанию: `https://api.deepseek.com` |
| `GROQ_API_KEY` | Для мини-программы | Получить на [console.groq.com](https://console.groq.com/) |
| `SMTP_SERVER` | Нет | SMTP-сервер для оповещений о рисках (например `smtp.qq.com`) |
| `SMTP_PORT` | Нет | SMTP-порт (QQ Mail: `465`) |
| `SMTP_USER` | Нет | Адрес электронной почты отправителя |
| `SMTP_PASSWORD` | Нет | SMTP-код авторизации (не пароль от почты) |
| `SMTP_RECEIVER` | Нет | Адрес получателя |
| `INTERNAL_TOKEN` | Нет | Токен авторизации между сервисами Java и Python |

> **Примечание**: `MYSQL_PASSWORD` — единственное действительно обязательное значение для запуска системы. Всё остальное имеет безопасные значения по умолчанию или корректно деградирует.

<details>
<summary><strong>Как получить SMTP-код авторизации QQ Mail</strong></summary>

1. Войдите на [mail.qq.com](https://mail.qq.com/) → Настройки → Аккаунт
2. Найдите раздел **POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV Service**
3. Включите **IMAP/SMTP Service**
4. Следуйте инструкции SMS-подтверждения для получения **кода авторизации**
5. Используйте этот код (не пароль QQ) в качестве `SMTP_PASSWORD`

</details>

### 3. Настройка Python-окружения

```bash
cd backend-ai

# Создание виртуального окружения
python3 -m venv venv

# Активация
source venv/bin/activate

# Установка зависимостей (только первый раз, ~2 мин)
pip install -r requirements.txt
```

При первом запуске будет загружена модель эмбеддингов `bge-small-zh-v1.5` (~90 МБ) с HuggingFace.

### 4. Настройка Java-окружения

```bash
cd backend-java

# Загрузка зависимостей и компиляция (только первый раз, ~3 мин)
mvn clean install -DskipTests
```

### 5. Инициализация базы данных

```bash
mysql -u root -p < sql/init.sql
```

Будут созданы:
- База данных `medvision` (UTF8MB4)
- Таблица `medicines` — информация о препаратах и полный текст
- Таблица `chat_logs` — история диалогов и аналитика
- Таблица `admin_users` — учётные записи администраторов

Учётная запись администратора по умолчанию (`admin` / `admin`) создаётся автоматически при первом запуске Java-бэкенда.

> **Альтернатива**: если пропустить этот шаг, Spring Boot с `hibernate.ddl-auto=update` автоматически создаст таблицы при запуске. SQL-скрипт предусмотрен для явного управления схемой и промышленного развёртывания.

## Использование

### Быстрый старт (все сервисы одновременно)

```bash
./start_all.sh
```

Скрипт запускает все сервисы в порядке зависимостей, дожидается готовности каждого и выводит статус. Логи записываются в `backend-ai/service.log`, `backend-java/backend.log` и `dashboard.log`.

### Ручной запуск (3 отдельных терминала)

**Терминал 1 — Python AI-сервис** (запускать первым, он самый медленный)

```bash
cd backend-ai
source venv/bin/activate
python main.py
```

Дождитесь: `Uvicorn running on http://0.0.0.0:8001`

> При первом запуске модель эмбеддингов (`bge-small-zh-v1.5`) будет загружена и закэширована. Последующие запуски занимают ~3 секунды.

**Терминал 2 — Java-бэкенд**

```bash
cd backend-java
mvn spring-boot:run
```

Дождитесь: `Started MedVisionApplication in X.XXX seconds`

> Maven загружает зависимости при первом запуске. Бэкенд автоматически создаст таблицы в базе данных и учётную запись администратора по умолчанию.

**Терминал 3 — Веб-интерфейс**

```bash
cd frontend
python3 -m http.server 5174
```

Откройте http://localhost:5174 в браузере.

**Опционально — Панель администратора**

```bash
streamlit run admin_dashboard.py --server.port 8502
```

Откройте http://localhost:8502. Логин: `admin` / `admin`.

### Остановка всех сервисов

```bash
./stop_all.sh
```

Или вручную:

```bash
lsof -t -i:5174 -i:8080 -i:8001 -i:8502 | xargs kill -9
```

## Мини-программа WeChat

### Настройка

1. Скачайте и установите [WeChat Developer Tools](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. Откройте инструмент, нажмите **Import Project**
3. Выберите директорию `frontend-wechat/`
4. Выберите **Test AppID** или гостевой режим
5. Отредактируйте `frontend-wechat/config.js`:

```js
const API_CANDIDATES = [
  'http://192.168.x.x:8080',  // замените на локальный IP вашего компьютера
];
```

### Определение локального IP

```bash
# macOS
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr "IPv4"
```

### Отладка на реальном устройстве

1. Убедитесь, что телефон и компьютер подключены к **одной сети Wi-Fi**
2. В WeChat Developer Tools нажмите **Debug on Device**
3. Отсканируйте QR-код телефоном
4. Если соединение не устанавливается, проверьте:
   - Брандмауэр компьютера разрешает порт `8080`
   - В `config.js` указан правильный локальный IP (не `localhost`)
   - Java-бэкенд запущен

## Конфигурация

### Смена модели LLM

Отредактируйте `backend-ai/core/config.py`:

```python
llm = ChatOpenAI(
    model="deepseek-v4-flash",   # измените модель здесь
    api_key=API_KEY,
    base_url=BASE_URL,
    temperature=0.3               # 0.0 = детерминированный, 1.0 = творческий
)
```

Доступные модели DeepSeek:
| Модель | Скорость | Стоимость | Рекомендуется для |
|--------|:--------:|:---------:|-------------------|
| `deepseek-v4-flash` | Быстрая | Очень низкая | Разработка, демонстрация (по умолчанию) |
| `deepseek-v4` | Средняя | Низкая | Более качественные ответы |

### Движок OCR

По умолчанию используется `ocrmac` (macOS Vision). Для переключения на Tesseract в Linux:

```bash
# Установка Tesseract с поддержкой китайского языка
sudo apt install tesseract-ocr tesseract-ocr-chi-sim

# Установка Python-обёртки
pip install pytesseract
```

Затем измените `backend-ai/services/ocr.py` для использования `pytesseract` вместо `ocrmac`.

### Модель эмбеддингов

Модель по умолчанию — `BAAI/bge-small-zh-v1.5` (оптимизирована для китайских медицинских текстов, ~90 МБ). Работает локально на CPU — вызовы API не требуются. Для смены:

```python
# backend-ai/core/config.py
embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",  # измените модель здесь
    model_kwargs={"local_files_only": True, "device": "cpu"}
)
```

> При первом использовании измените `local_files_only` на `False` для загрузки с HuggingFace.

### Ключевые слова риска

Отредактируйте `risk_keywords.json`, чтобы добавить или удалить триггерные слова:

```json
{
  "keywords": ["过量", "中毒", "过敏", "禁忌", "副作用", "..."]
}
```

При появлении любого ключевого слова в вопросе пользователя или ответе ИИ система фиксирует событие и (при настройке) отправляет email-уведомление.

### Безопасность панели администратора

Панель администратора ограничивает доступ по IP-адресам. Настройка в `backend-java/src/main/resources/application.properties`:

```properties
admin.security.enabled=true
admin.security.ip-whitelist=127.0.0.1,::1
```

Добавьте свой IP в белый список для удалённого доступа.

### Первоначальная настройка модели эмбеддингов

Модель эмбеддингов кэшируется локально после первой загрузки. Для принудительного повторного скачивания:

```bash
cd backend-ai
source venv/bin/activate
python -c "from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='BAAI/bge-small-zh-v1.5')"
```

## API-эндпоинты

### Python AI-сервис (`:8001`)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/health` | Проверка работоспособности |
| `POST` | `/ocr` | OCR изображения/PDF/Word → извлечение текста |
| `POST` | `/chat` | RAG ответы на вопросы |
| `POST` | `/transcribe` | Распознавание речи (Whisper через Groq) |
| `POST` | `/analyze` | Ручной анализ текста |
| `GET` | `/tts` | Синтез речи (edge-tts) |
| `GET` | `/search` | Поиск по истории лекарств |

### Java-бэкенд (`:8080`)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api/medicine/health` | Проверка работоспособности |
| `POST` | `/api/medicine/recognize` | Загрузка и распознавание инструкции к препарату |
| `POST` | `/api/medicine/chat` | Проксирование в AI-сервис для чата |
| `GET` | `/api/medicine/list` | Список всех сохранённых препаратов |
| `GET` | `/api/medicine/chat-logs` | История чатов (для администратора) |
| `GET` | `/api/medicine/analytics` | Аналитика использования (для администратора) |
| `POST` | `/api/medicine/admin/login` | Вход администратора |

## Тестирование

```bash
# Юнит-тесты Python (17 тестов, ~0.2 с)
cd backend-ai
source venv/bin/activate
python -m pytest tests/ -v

# Юнит-тесты Java (6 тестов)
cd backend-java
mvn test
```

### Покрытие тестами

| Модуль | Тесты | Что покрывают |
|--------|:-----:|---------------|
| `check_risk_keywords` | 6 | Совпадение, кэш, истечение, пустой ввод |
| `smart_rag_search` | 4 | Короткий текст, длинный текст, откат при ошибке, граничные случаи |
| `correct_medical_terms` | 7 | Фильтр галлюцинаций, чёрный список, коррекция LLM, откат при ошибке |
| `MedicineController` | 6 | MockMvc-тесты REST-эндпоинтов |

## Структура проекта

```
MedVision-RAG/
├── frontend/                  # Vue 3 одностраничное веб-приложение
│   └── index.html             # Полный фронтенд (848 строк)
├── frontend-wechat/           # Мини-программа WeChat
│   ├── pages/index/           # Главная страница (WXML + JS + WXSS)
│   ├── app.js                 # Точка входа приложения
│   └── config.js              # Конфигурация API-эндпоинтов
├── backend-java/              # Spring Boot бизнес-бэкенд
│   ├── src/main/java/com/medvision/
│   │   ├── controller/        # REST-эндпоинты
│   │   ├── service/           # Бизнес-логика
│   │   ├── entity/            # JPA-сущности (Medicine, ChatLog, AdminUser)
│   │   ├── repository/        # Репозитории Spring Data JPA
│   │   └── config/            # Безопасность, CORS, IP-список, инициализация данных
│   ├── src/test/              # MockMvc-тесты
│   └── pom.xml                # Maven-зависимости
├── backend-ai/                # FastAPI AI-сервис
│   ├── main.py                # Точка входа маршрутов (~250 строк)
│   ├── core/
│   │   ├── config.py          # Глобальные синглтоны (LLM, эмбеддинги, Groq-клиент)
│   │   ├── logging_config.py  # Структурированное логирование + middleware трассировки
│   │   └── security.py        # Верификация внутреннего токена
│   ├── services/
│   │   ├── ocr.py             # OCR (ocrmac + Tesseract как запасной вариант)
│   │   ├── asr.py             # Распознавание речи (Groq Whisper)
│   │   ├── rag.py             # Адаптивный RAG (context stuffing + векторный поиск)
│   │   ├── tts.py             # Синтез речи (edge-tts)
│   │   ├── risk.py            # Обнаружение ключевых слов риска + TTL-кэш
│   │   ├── email.py           # Email-оповещения о рисках (асинхронный пул потоков)
│   │   ├── intent.py          # Анализ намерений (текущий vs исторический препарат)
│   │   ├── search.py          # Поиск по истории лекарств
│   │   └── chat_model.py      # Переключение чат-модели
│   ├── models/
│   │   └── schemas.py         # Pydantic-модели запросов
│   └── tests/                 # Юнит-тесты pytest
├── admin_dashboard.py         # Панель администратора на Streamlit
├── risk_keywords.json         # Словарь ключевых слов риска
├── sql/
│   └── init.sql               # Скрипт инициализации базы данных
├── Package-Insert_Test/       # Примеры инструкций для тестирования
├── .env.example               # Шаблон переменных окружения
├── .gitignore                 # Правила Git
├── start_all.sh               # Единый скрипт запуска всех сервисов
└── stop_all.sh                # Единый скрипт остановки всех сервисов
```

## Часто задаваемые вопросы

### Установка и запуск

**`No module named 'ocrmac'`**

`ocrmac` использует фреймворк macOS Vision и работает только на macOS. Для Linux установите Tesseract:

```bash
sudo apt install tesseract-ocr tesseract-ocr-chi-sim
pip install pytesseract
```

Затем измените `backend-ai/services/ocr.py` для использования `pytesseract`.

**`Connection refused` при запуске Java-бэкенда**

MySQL не запущен или указан неверный пароль.

```bash
# Проверка состояния MySQL
mysql -u root -p -e "SELECT 1"

# Проверка пароля в .env
cat .env | grep MYSQL_PASSWORD
```

**Предупреждение `torchaudio` при запуске Python**

Это некритичное предупреждение о VAD (Voice Activity Detection). Система автоматически переключается в режим без VAD и работает нормально. Для исправления: `pip install torchaudio`.

**Maven загружает зависимости медленно**

Добавьте зеркало в `~/.m2/settings.xml`:

```xml
<mirrors>
  <mirror>
    <id>aliyun</id>
    <mirrorOf>central</mirrorOf>
    <url>https://maven.aliyun.com/repository/central</url>
  </mirror>
</mirrors>
```

### Использование

**Белый экран в браузере**

Откройте DevTools (F12) → вкладка Console. Типичные причины:
- AI-сервис не запущен → проверьте порт `8001`
- Java-бэкенд не запущен → проверьте порт `8080`
- Ошибка CORS → убедитесь, что вы обращаетесь через `localhost:5174`, а не `file://`

**Мини-программа не подключается к бэкенду**

1. Убедитесь, что телефон и компьютер подключены к **одной сети Wi-Fi**
2. Проверьте, что в `config.js` указан локальный IP (не `localhost` или `127.0.0.1`)
3. Убедитесь, что брандмауэр компьютера разрешает входящие подключения на порту `8080`
4. Попробуйте `curl http://YOUR_LAN_IP:8080/api/medicine/health` из браузера телефона

**Распознавание речи не работает (веб)**

Браузеры требуют HTTPS или `localhost` для доступа к микрофону. Убедитесь, что вы открываете страницу через `http://localhost:5174`, а не через локальный IP.

**Распознавание речи не работает (мини-программа)**

Проверьте, что `GROQ_API_KEY` указан в `.env`. Перезапустите Python AI-сервис после изменения `.env`.

**OCR возвращает "неизвестный препарат" или искажённый текст**

- Убедитесь, что фотография чёткая и хорошо освещённая
- Название препарата должно быть видно на изображении
- Для PDF проверьте, является ли файл отсканированным изображением (не текстовым) — система автоматически определит и использует OCR изображений

### База данных

**Как сбросить базу данных**

```bash
mysql -u root -p -e "DROP DATABASE IF EXISTS medvision;"
mysql -u root -p < sql/init.sql
```

Затем перезапустите Java-бэкенд для повторного создания учётной записи администратора по умолчанию.

**Как изменить пароль администратора**

Используйте панель администратора (http://localhost:8502) после входа или обновите напрямую в MySQL:

```sql
USE medvision;
UPDATE admin_users SET password_hash = '$2a$10$...' WHERE username = 'admin';
```

Сгенерируйте хеш BCrypt с помощью любого онлайн-инструмента или Python:

```python
from passlib.hash import bcrypt
print(bcrypt.hash("your_new_password"))
```

## Лицензия

MIT
