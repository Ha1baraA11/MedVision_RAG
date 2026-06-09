<p align="center">
  <img src="assets/logo.png" alt="MedVision-RAG Logo" width="200">
</p>

<h1 align="center">MedVision-RAG</h1>

<p align="center">
  <strong>KI-gestuetzter Medikamentenassistent mit Sprachinteraktion</strong><br>
  Foto des Beipackzettels aufnehmen -- sofortige Antworten ueber RAG + Sprache.
</p>

<p align="center">
  <a href="README.md">English</a> · <a href="README_CN.md">简体中文</a> · <a href="README_TW.md">繁體中文</a> · <a href="README_ja.md">日本語</a> · <a href="README_ko.md">한국어</a> · <a href="README_es.md">Español</a> · <a href="README_pt-BR.md">Português</a> · <a href="README_ru.md">Русский</a> · <a href="README_fr.md">Français</a>
</p>

---

## Was das System macht

MedVision-RAG hilft sehbehinderten und aelteren Nutzern, ihre Medikamente zu verstehen. Richten Sie die Kamera auf eine Medikamentenverpackung oder laden Sie eine PDF/Word-Datei hoch -- das System:

1. **Extrahiert Text** per OCR (macOS Vision / Tesseract als Fallback)
2. **Bereinigt den Text** ueber die Unstructured.io-Pipeline (Leerzeichen, abgebrochene Absaetze, Aufzaehlungspunkte)
3. **Erstellt eine Wissensbasis** durch Vektorisierung des Textes in ChromaDB
4. **Beantwortet Fragen** mit adaptivem RAG -- kurze Texte verwenden direktes Context Stuffing, lange Texte nutzen Vektor-Aehnlichkeitssuche
5. **Liest die Antwort vor** ueber edge-tts

Das System unterstuetzt einen **Webbrowser**, ein **WeChat-Mini-Programm** sowie ein **Admin-Dashboard** zur Ueberwachung von Chatprotokollen und Analysen.

## Funktionen

### Multi-Format-OCR
- **Fotos**: Medikamentenverpackungen, Schachteln, Blister direkt per Kamera
- **PDF**: Sowohl textbasiert als auch gescannt (automatische Erkennung und Rendern zu Bild fuer OCR)
- **Word**: Extrahiert Text und Tabellen; greift auf eingebettete Bild-OCR zurueck, wenn der Text unzureichend ist
- **HEIC/HEIF**: iPhone-Fotos werden vor der OCR automatisch in JPEG konvertiert

### Adaptiver RAG-Engine
- **Kurzer Text** (< 1.500 Zeichen): Context Stuffing -- das gesamte Dokument wird in den LLM-Prompt eingespeist
- **Langer Text** (>= 1.500 Zeichen): Vektorsuche -- Aufteilung in Chunks, Speicherung in ChromaDB, Abruf der relevantesten Top-K-Passagen
- **Medikamentenwechsel**: Erwaehnt der Nutzer ein anderes Medikament, wechselt das System automatisch den Kontext

### Sprachinteraktion
- **Web**: Browser-eigene Speech Recognition API (null Latenz, keine API-Kosten)
- **Mini-Programm**: Groq Whisper Large-V3 fuer Speech-to-Text, edge-tts fuer Text-to-Speech
- **Korrektur medizinischer Fachbegriffe**: LLM nachbearbeitet die ASR-Ausgabe, um fehlerhafte Medikamentennamen zu korrigieren
- **Unterbrechbare Wiedergabe**: Druecken Sie die Sprechtaste, um die laufende TTS- Ausgabe sofort zu stoppen

### Risikoerkennung
- **Schluesselworterkennung**: Konfigurierbare Risiko-Schluesselwoerter in `risk_keywords.json`
- **Chatprotokoll-Audit**: Alle Gespeicherte Unterhaltungen in MySQL zur Pruefung
- **E-Mail-Benachrichtigungen**: Automatische E-Mail bei ausgeloesten Risiko-Schluesselwoertern (konfigurierbar)
- **Admin-Dashboard**: Echtzeitueberwachung ueber Streamlit mit IP-Whitelist-Schutz

### Barrierefreiheit
- Hochkontrast-UI (WCAG AA-konform)
- Grosse Touch-Ziele (48px+)
- Vollstaendig sprachgesteuerter Workflow fuer sehbehinderte Nutzer
- Chinesisch/Englisch-Umschaltung mit synchronisierter KI-Antwort und TTS-Sprache

## Architektur

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

## Voraussetzungen

| Abhaengigkeit | Version | Hinweise |
|:-----------|:-------:|-------|
| Python | 3.10+ | Laufzeitumgebung fuer den KI-Dienst |
| Java | 17+ | Laufzeitumgebung fuer das Business-Backend |
| Maven | 3.8+ | Java-Build-Tool |
| MySQL | 8.0+ | Relationale Datenspeicherung |
| macOS (empfohlen) | 13+ | `ocrmac` verwendet das Apple Vision-Framework fuer OCR |

> **Linux**: Wird unterstuetzt, erfordert aber [Tesseract](https://github.com/tesseract-ocr/tesseract) fuer die OCR. Installieren Sie es ueber `apt install tesseract-ocr tesseract-ocr-chi-sim` und passen Sie `backend-ai/services/ocr.py` entsprechend an.

## API-Schluessel

Sie benoetigen einen **DeepSeek API Key** (zwingend erforderlich) und optional einen **Groq API Key** (fuer die Spracherkennung im WeChat-Mini-Programm).

<details>
<summary><strong>DeepSeek API Key erhalten (zwingend erforderlich)</strong></summary>

DeepSeek stellt das LLM fuer die Fragebeantwortung bereit.

1. Besuchen Sie [platform.deepseek.com](https://platform.deepseek.com/)
2. Registrieren Sie sich oder melden Sie sich an
3. Navigieren Sie in der linken Seitenleiste zu **API Keys**
4. Klicken Sie auf **Create API Key** und vergeben Sie einen Namen (z. B. "MedVision")
5. Kopieren Sie den Schluessel sofort (er beginnt mit `sk-` und wird nicht erneut angezeigt)

**Kosten**: Das Standardmodell `deepseek-v4-flash` ist ausserst guenstig. Ein ganzer Entwicklungstag kostet in der Regel weniger als 0,01 $.

</details>

<details>
<summary><strong>Groq API Key erhalten (optional -- nur fuer Mini-Programm)</strong></summary>

Groq bietet schnelle Spracherkennung ueber Whisper Large-V3 auf LPU-Hardware.

1. Besuchen Sie [console.groq.com](https://console.groq.com/)
2. Registrieren Sie sich mit GitHub- oder Google-Konto
3. Navigieren Sie in der linken Seitenleiste zu **API Keys**
4. Klicken Sie auf **Create API Key**
5. Kopieren Sie den Schluessel (beginnt mit `gsk-`)

**Kosten**: Das kostenlose Kontingent beinhaltet ein grosszuegiges Whisper-Kontingent. Das Web-Frontend verwendet die eingebaute Browser-Sprach-API und verbraucht **keine** Groq-Guthaben -- nur das WeChat-Mini-Programm nutzt Groq.

</details>

## Installation

### 1. Repository klonen

```bash
git clone https://github.com/Ha1baraA11/MedVision_RAG.git
cd MedVision_RAG
```

### 2. Umgebung konfigurieren

```bash
cp .env.example .env
```

Oeffnen Sie `.env` in einem Texteditor und tragen Sie Ihre Werte ein:

```bash
# macOS
open -e .env

# VS Code
code .env
```

| Variable | Erforderlich | Beschreibung |
|----------|:--------:|-------------|
| `MYSQL_PASSWORD` | **Ja** | Ihr MySQL-Root-Passwort |
| `DEEPSEEK_API_KEY` | **Ja** | Von [platform.deepseek.com](https://platform.deepseek.com/) |
| `DEEPSEEK_BASE_URL` | Nein | Standard: `https://api.deepseek.com` |
| `GROQ_API_KEY` | Mini-Programm | Von [console.groq.com](https://console.groq.com/) |
| `SMTP_SERVER` | Nein | SMTP-Server fuer Risiko-Benachrichtigungen (z. B. `smtp.qq.com`) |
| `SMTP_PORT` | Nein | SMTP-Port (QQ Mail: `465`) |
| `SMTP_USER` | Nein | Absender-E-Mail-Adresse |
| `SMTP_PASSWORD` | Nein | SMTP-Autorisierungscode (nicht Ihr E-Mail-Passwort) |
| `SMTP_RECEIVER` | Nein | Empfaenger-E-Mail-Adresse |
| `INTERNAL_TOKEN` | Nein | Authentifizierungstoken zwischen Java- und Python-Diensten |

> **Hinweis**: `MYSQL_PASSWORD` ist die einzige Anmeldedaten, die zwingend erforderlich ist, damit das System startet. Alles uebrige hat sichere Standardwerte oder einen graceful Fallback.

<details>
<summary><strong>QQ Mail SMTP-Autorisierungscode erhalten</strong></summary>

1. Melden Sie sich bei [mail.qq.com](https://mail.qq.com/) an -> Einstellungen -> Konto
2. Suchen Sie **POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV-Dienst**
3. Aktivieren Sie **IMAP/SMTP-Dienst**
4. Folgen Sie der SMS-Verifizierung, um einen **Autorisierungscode** zu erhalten
5. Verwenden Sie diesen Code (nicht Ihr QQ-Passwort) als `SMTP_PASSWORD`

</details>

### 3. Python-Umgebung einrichten

```bash
cd backend-ai

# Virtuelle Umgebung erstellen
python3 -m venv venv

# Aktivieren
source venv/bin/activate

# Abhaengigkeiten installieren (nur beim ersten Mal, dauert ca. 2 Min.)
pip install -r requirements.txt
```

Beim ersten Start wird das Embedding-Modell `bge-small-zh-v1.5` (~90 MB) von HuggingFace heruntergeladen.

### 4. Java-Umgebung einrichten

```bash
cd backend-java

# Abhaengigkeiten herunterladen und kompilieren (nur beim ersten Mal, dauert ca. 3 Min.)
mvn clean install -DskipTests
```

### 5. Datenbank initialisieren

```bash
mysql -u root -p < sql/init.sql
```

Dies erstellt:
- Datenbank `medvision` (UTF8MB4)
- Tabelle `medicines` -- Medikamenteninformationen und Volltext
- Tabelle `chat_logs` -- Unterhaltungsverlauf und Analysen
- Tabelle `admin_users` -- Admin-Konten

Das Standard-Admin-Konto (`admin` / `admin`) wird beim ersten Start des Java-Backends automatisch erstellt.

> **Alternative**: Ueberspringen Sie diesen Schritt, so erstellt Spring Boot mit `hibernate.ddl-auto=update` die Tabellen beim Start automatisch. Das SQL-Skript dient der expliziten Schema-Verwaltung und produktiven Einsaetzen.

## Verwendung

### Schnellstart (alle Dienste gleichzeitig)

```bash
./start_all.sh
```

Dieses Skript startet alle Dienste in der Abhaengigkeitsreihenfolge, wartet auf deren Bereitschaft und gibt den Status aus. Logs werden in `backend-ai/service.log`, `backend-java/backend.log` und `dashboard.log` geschrieben.

### Manueller Start (3 separate Terminals)

**Terminal 1 -- Python-KI-Dienst** (zuerst starten, da am langsamsten)

```bash
cd backend-ai
source venv/bin/activate
python main.py
```

Warten Sie auf: `Uvicorn running on http://0.0.0.0:8001`

> Beim ersten Start wird das Embedding-Modell (`bge-small-zh-v1.5`) heruntergeladen und zwischengespeichert. Nachfolgende Starts dauern ca. 3 Sekunden.

**Terminal 2 -- Java-Backend**

```bash
cd backend-java
mvn spring-boot:run
```

Warten Sie auf: `Started MedVisionApplication in X.XXX seconds`

> Laedt Maven beim ersten Durchlauf die Abhaengigkeiten herunter. Das Backend erstellt automatisch die Datenbanktabellen und das Standard-Admin-Konto.

**Terminal 3 -- Web-Frontend**

```bash
cd frontend
python3 -m http.server 5174
```

Oeffnen Sie http://localhost:5174 in Ihrem Browser.

**Optional -- Admin-Dashboard**

```bash
streamlit run admin_dashboard.py --server.port 8502
```

Oeffnen Sie http://localhost:8502. Login: `admin` / `admin`.

### Alle Dienste stoppen

```bash
./stop_all.sh
```

Oder manuell:

```bash
lsof -t -i:5174 -i:8080 -i:8001 -i:8502 | xargs kill -9
```

## WeChat-Mini-Programm

### Einrichtung

1. Laden Sie die [WeChat Developer Tools](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html) herunter und installieren Sie sie
2. Oeffnen Sie das Tool und klicken Sie auf **Import Project**
3. Waehlen Sie das Verzeichnis `frontend-wechat/` aus
4. Waehlen Sie **Test AppID** oder den Gastmodus
5. Bearbeiten Sie `frontend-wechat/config.js`:

```js
const API_CANDIDATES = [
  'http://192.168.x.x:8080',  // Ersetzen Sie dies durch die LAN-IP Ihres Computers
];
```

### LAN-IP ermitteln

```bash
# macOS
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr "IPv4"
```

### Debugging auf dem Geraet

1. Stellen Sie sicher, dass Ihr Telefon und Computer im **selben WLAN-Netzwerk** sind
2. Klicken Sie in den WeChat Developer Tools auf **Debug on Device**
3. Scannen Sie den QR-Code mit Ihrem Telefon
4. Wenn die Verbindung fehlschlaegt, pruefen Sie:
   - Die Computer-Firewall erlaubt Port `8080`
   - `config.js` enthaelt die korrekte LAN-IP (nicht `localhost`)
   - Das Java-Backend laeuft

## Konfiguration

### LLM-Modell wechseln

Bearbeiten Sie `backend-ai/core/config.py`:

```python
llm = ChatOpenAI(
    model="deepseek-v4-flash",   # Modell hier aendern
    api_key=API_KEY,
    base_url=BASE_URL,
    temperature=0.3               # 0.0 = deterministisch, 1.0 = kreativ
)
```

Verfuegbare DeepSeek-Modelle:
| Modell | Geschwindigkeit | Kosten | Empfohlen fuer |
|-------|:-----:|:----:|-----------------|
| `deepseek-v4-flash` | Schnell | Sehr niedrig | Entwicklung, Demo (Standard) |
| `deepseek-v4` | Mittel | Niedrig | Bessere Antwortqualitaet |

### OCR-Engine

`ocrmac` (macOS Vision) wird standardmaessig verwendet. Um auf Linux zu Tesseract zu wechseln:

```bash
# Tesseract mit Chinesisch-Unterstuetzung installieren
sudo apt install tesseract-ocr tesseract-ocr-chi-sim

# Python-Wrapper installieren
pip install pytesseract
```

Passen Sie dann `backend-ai/services/ocr.py` an, um `pytesseract` anstelle von `ocrmac` zu verwenden.

### Embedding-Modell

Das Standardmodell ist `BAAI/bge-small-zh-v1.5` (optimiert fuer chinesische medizinische Texte, ~90 MB). Es laeuft lokal auf der CPU -- es werden keine API-Aufufe benoetigt. Zum Aendern:

```python
# backend-ai/core/config.py
embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",  # Modell hier aendern
    model_kwargs={"local_files_only": True, "device": "cpu"}
)
```

> Aendern Sie `local_files_only` beim ersten Gebrauch auf `False`, um das Modell von HuggingFace herunterzuladen.

### Risiko-Schluesselwoerter

Bearbeiten Sie `risk_keywords.json`, um Ausloeserwoerter hinzuzufuegen oder zu entfernen:

```json
{
  "keywords": ["过量", "中毒", "过敏", "禁忌", "副作用", "..."]
}
```

Erscheint eines der Schluesselwoerter in der Frage des Nutzers oder in der KI-Antwort, protokolliert das System das Ereignis und sendet (sofern konfiguriert) eine E-Mail-Benachrichtigung.

### Admin-Dashboard-Sicherheit

Das Admin-Dashboard schraenkt den Zugriff per IP-Whitelist ein. Konfiguration in `backend-java/src/main/resources/application.properties`:

```properties
admin.security.enabled=true
admin.security.ip-whitelist=127.0.0.1,::1
```

Fuegen Sie bei Fernzugriff Ihre IP zur Whitelist hinzu.

### Ersteinrichtung des Embedding-Modells

Das Embedding-Modell wird nach dem ersten Download lokal zwischengespeichert. Wenn ein erneuter Download erzwungen werden soll:

```bash
cd backend-ai
source venv/bin/activate
python -c "from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='BAAI/bge-small-zh-v1.5')"
```

## API-Endpunkte

### Python-KI-Dienst (`:8001`)

| Methode | Pfad | Beschreibung |
|--------|------|-------------|
| `GET` | `/health` | Gesundheitspruefung |
| `POST` | `/ocr` | OCR Bild/PDF/Word -> Text extrahieren |
| `POST` | `/chat` | RAG-Fragebeantwortung |
| `POST` | `/transcribe` | Sprache-zu-Text (Whisper ueber Groq) |
| `POST` | `/analyze` | Manuelle Textanalyse |
| `GET` | `/tts` | Text-zu-Sprache (edge-tts) |
| `GET` | `/search` | Medikamentenverlauf durchsuchen |

### Java-Backend (`:8080`)

| Methode | Pfad | Beschreibung |
|--------|------|-------------|
| `GET` | `/api/medicine/health` | Gesundheitspruefung |
| `POST` | `/api/medicine/recognize` | Beipackzettel hochladen und erkennen |
| `POST` | `/api/medicine/chat` | Proxy an den KI-Dienst Chat |
| `GET` | `/api/medicine/list` | Alle gespeicherten Medikamente auflisten |
| `GET` | `/api/medicine/chat-logs` | Chatprotokoll-Verlauf (Admin) |
| `GET` | `/api/medicine/analytics` | Nutzungsanalysen (Admin) |
| `POST` | `/api/medicine/admin/login` | Admin-Login |

## Tests

```bash
# Python-Tests (17 Tests, ca. 0,2 s)
cd backend-ai
source venv/bin/activate
python -m pytest tests/ -v

# Java-Tests (6 Tests)
cd backend-java
mvn test
```

### Testabdeckung

| Modul | Tests | Abdeckung |
|--------|:-----:|--------|
| `check_risk_keywords` | 6 | Treffer, Cache, Ablauf, leere Eingabe |
| `smart_rag_search` | 4 | Kurzer Text, langer Text, Fehler-Fallback, Randfaelle |
| `correct_medical_terms` | 7 | Halluzinationsfilter, Blacklist, LLM-Korrektur, Fehler-Fallback |
| `MedicineController` | 6 | REST-Endpunkt-MockMvc-Tests |

## Projektstruktur

```
MedVision-RAG/
├── frontend/                  # Vue 3 Single-File-Web-App
│   └── index.html             # Komplettes Frontend (848 Zeilen)
├── frontend-wechat/           # WeChat-Mini-Programm
│   ├── pages/index/           # Hauptseite (WXML + JS + WXSS)
│   ├── app.js                 # App-Einstiegspunkt
│   └── config.js              # API-Endpunkt-Konfiguration
├── backend-java/              # Spring Boot Business-Backend
│   ├── src/main/java/com/medvision/
│   │   ├── controller/        # REST-Endpunkte
│   │   ├── service/           # Business-Logik
│   │   ├── entity/            # JPA-Entities (Medicine, ChatLog, AdminUser)
│   │   ├── repository/        # Spring Data JPA Repositories
│   │   └── config/            # Sicherheit, CORS, IP-Whitelist, Dateninitialisierung
│   ├── src/test/              # MockMvc-Tests
│   └── pom.xml                # Maven-Abhaengigkeiten
├── backend-ai/                # FastAPI-KI-Dienst
│   ├── main.py                # Routen-Einstiegspunkt (~250 Zeilen)
│   ├── core/
│   │   ├── config.py          # Globale Singletons (LLM, Embedding, Groq-Client)
│   │   ├── logging_config.py  # Strukturiertes Logging + Trace-Middleware
│   │   └── security.py        # Internes Token-Verifizierung
│   ├── services/
│   │   ├── ocr.py             # OCR (ocrmac + Tesseract-Fallback)
│   │   ├── asr.py             # Spracherkennung (Groq Whisper)
│   │   ├── rag.py             # Adaptives RAG (Context Stuffing + Vektorsuche)
│   │   ├── tts.py             # Text-zu-Sprache (edge-tts)
│   │   ├── risk.py            # Risiko-Schluesselworterkennung + TTL-Cache
│   │   ├── email.py           # Risiko-Benachrichtigung per E-Mail (asynchroner Thread-Pool)
│   │   ├── intent.py          # Intent-Analyse (aktuelles vs. historisches Medikament)
│   │   ├── search.py          # Medikamentenverlauf-Suche
│   │   └── chat_model.py      # Chat-Modell-Switching
│   ├── models/
│   │   └── schemas.py         # Pydantic-Request-Modelle
│   └── tests/                 # pytest-Tests
├── admin_dashboard.py         # Streamlit Admin-Dashboard
├── risk_keywords.json         # Risiko-Schluesselwort-Verzeichnis
├── sql/
│   └── init.sql               # Datenbank-Initialisierungsskript
├── Package-Insert_Test/       # Beispiel-Beipackzettel zum Testen
├── .env.example               # Umgebungsvariablen-Vorlage
├── .gitignore                 # Git-Ignore-Regeln
├── start_all.sh               # Alle Dienste mit einem Befehl starten
└── stop_all.sh                # Alle Dienste mit einem Befehl stoppen
```

## Haeufig gestellte Fragen

### Installation und Start

**`No module named 'ocrmac'`**

`ocrmac` verwendet das macOS Vision-Framework und funktioniert nur unter macOS. Fuer Linux installieren Sie Tesseract:

```bash
sudo apt install tesseract-ocr tesseract-ocr-chi-sim
pip install pytesseract
```

Passen Sie dann `backend-ai/services/ocr.py` an, um `pytesseract` zu verwenden.

**`Connection refused` beim Start des Java-Backends**

MySQL laeuft nicht oder das Passwort ist falsch.

```bash
# MySQL-Status pruefen
mysql -u root -p -e "SELECT 1"

# Ueberpruefen, ob das .env-Passwort mit Ihrem MySQL-Root-Passwort uebereinstimmt
cat .env | grep MYSQL_PASSWORD
```

**`torchaudio`-Warnung beim Python-Start**

Dies ist eine nicht-fatale Warnung ueber VAD (Voice Activity Detection). Das System greift auf den VAD-freien Modus zurueck und funktioniert einwandfrei. Zur Behebung: `pip install torchaudio`.

**Maven-Download ist langsam**

Fuegen Sie einen Mirror in `~/.m2/settings.xml` ein:

```xml
<mirrors>
  <mirror>
    <id>aliyun</id>
    <mirrorOf>central</mirrorOf>
    <url>https://maven.aliyun.com/repository/central</url>
  </mirror>
</mirrors>
```

### Verwendung

**Weisser Bildschirm im Browser**

Oeffnen Sie die DevTools (F12) -> Konsole. Haeufige Ursachen:
- KI-Dienst nicht gestartet -> Port `8001` pruefen
- Java-Backend nicht gestartet -> Port `8080` pruefen
- CORS-Fehler -> Stellen Sie sicher, dass Sie ueber `localhost:5174` zugreifen, nicht ueber `file://`

**Mini-Programm kann sich nicht mit dem Backend verbinden**

1. Ueberpruefen Sie, ob Telefon und Computer im **selben WLAN-Netzwerk** sind
2. Pruefen Sie, ob `config.js` Ihre LAN-IP enthaelt (nicht `localhost` oder `127.0.0.1`)
3. Pruefen Sie, ob die Computer-Firewall eingehende Verbindungen auf Port `8080` erlaubt
4. Versuchen Sie `curl http://YOUR_LAN_IP:8080/api/medicine/health` im Browser Ihres Telefons

**Spracherkennung funktioniert nicht (Web)**

Browser erfordern HTTPS oder `localhost` fuer Mikrofonzugriff. Stellen Sie sicher, dass Sie die Seite ueber `http://localhost:5174` aufrufen, nicht ueber eine LAN-IP.

**Spracherkennung funktioniert nicht (Mini-Programm)**

Pruefen Sie, ob `GROQ_API_KEY` in `.env` gesetzt ist. Starten Sie den Python-KI-Dienst nach Aenderungen an `.env` neu.

**OCR liefert "unknown drug" oder unleserlichen Text**

- Stellen Sie sicher, dass das Foto klar und gut beleuchtet ist
- Der Medikamentenname sollte im Bild sichtbar sein
- Bei PDFs pruefen Sie, ob die Datei ein gescanntes Bild ist (kein durchsuchbarer Text) -- das System erkennt dies automatisch und verwendet Bild-OCR

### Datenbank

**Datenbank zuruecksetzen**

```bash
mysql -u root -p -e "DROP DATABASE IF EXISTS medvision;"
mysql -u root -p < sql/init.sql
```

Starten Sie anschliessend das Java-Backend neu, um das Standard-Admin-Konto neu zu erstellen.

**Admin-Passwort aendern**

Verwenden Sie das Admin-Dashboard (http://localhost:8502) nach dem Login, oder aktualisieren Sie direkt in MySQL:

```sql
USE medvision;
UPDATE admin_users SET password_hash = '$2a$10$...' WHERE username = 'admin';
```

Erzeugen Sie einen BCrypt-Hash ueber ein Online-Tool oder mit Python:

```python
from passlib.hash import bcrypt
print(bcrypt.hash("your_new_password"))
```

## Lizenz

MIT
