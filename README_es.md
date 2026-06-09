<p align="center">
  <img src="assets/logo.png" alt="MedVision-RAG Logo" width="200">
</p>

<h1 align="center">MedVision-RAG</h1>

<p align="center">
  <strong>Asistente de medicación potenciado por IA con interacción por voz</strong><br>
  Toma una foto de cualquier prospecto de medicamento y obtén respuestas al instante mediante RAG + voz.
</p>

<p align="center">
  <a href="README.md">English</a> · <a href="README_CN.md">简体中文</a> · <a href="README_TW.md">繁體中文</a> · <a href="README_ja.md">日本語</a> · <a href="README_ko.md">한국어</a> · <a href="README_pt-BR.md">Português</a> · <a href="README_ru.md">Русский</a> · <a href="README_fr.md">Français</a> · <a href="README_de.md">Deutsch</a>
</p>

---

## ¿Qué hace?

MedVision-RAG ayuda a personas con discapacidad visual y adultos mayores a entender su medicación. Apunta la cámara a un envase de medicamento o sube un archivo PDF/Word, y el sistema:

1. **Extrae el texto** mediante OCR (macOS Vision / Tesseract como respaldo)
2. **Limpia el texto** usando el pipeline de Unstructured.io (espacios en blanco, párrafos rotos, viñetas)
3. **Construye una base de conocimiento** vectorizando el texto en ChromaDB
4. **Responde preguntas** usando RAG adaptativo: para textos cortos inyecta el contexto completo directamente, para textos largos usa búsqueda por similitud vectorial
5. **Lee la respuesta en voz alta** mediante edge-tts

El sistema es compatible con **navegador web**, **Mini Program de WeChat** y un **panel de administración** para monitorear registros de chat y analíticas.

## Funcionalidades

### OCR multi-formato
- **Fotos**: Envases, cajas, blisters — directamente desde la cámara
- **PDF**: Tanto basados en texto como escaneados (detecta automáticamente y renderiza a imagen para OCR)
- **Word**: Extrae texto y tablas; recurre a OCR de imágenes incrustadas cuando el texto no es suficiente
- **HEIC/HEIF**: Las fotos de iPhone se convierten automáticamente a JPEG antes del OCR

### Motor RAG adaptativo
- **Texto corto** (< 1500 caracteres): Context Stuffing — inyecta el documento completo en el prompt del LLM
- **Texto largo** (>= 1500 caracteres): Búsqueda vectorial — divide en fragmentos, almacena en ChromaDB y recupera los pasajes más relevantes (top-K)
- **Cambio entre medicamentos**: Cuando el usuario menciona un medicamento diferente por nombre, el sistema cambia el contexto automáticamente

### Interacción por voz
- **Web**: API de reconocimiento de voz nativa del navegador (sin latencia, sin costo de API)
- **Mini Program**: Groq Whisper Large-V3 para voz-a-texto, edge-tts para texto-a-voz
- **Corrección de términos médicos**: El LLM post-procesa la salida del ASR para corregir nombres de medicamentos mal reconocidos
- **Reproducción interrumpible**: Presiona el botón de voz para detener inmediatamente el TTS en curso

### Monitoreo de riesgos
- **Detección por palabras clave**: Palabras clave de riesgo configurables en `risk_keywords.json`
- **Auditoría de chats**: Todas las conversaciones se almacenan en MySQL para su revisión
- **Alertas por correo**: Notificación automática por email cuando se activan palabras clave de riesgo (configurable)
- **Panel de administración**: Monitoreo en tiempo real mediante Streamlit con protección por lista blanca de IPs

### Accesibilidad
- Interfaz de alto contraste (cumple con WCAG AA)
- Áreas de toque grandes (48px+)
- Flujo de trabajo completamente por voz para usuarios con discapacidad visual
- Cambio de idioma chino/inglés con sincronización entre la respuesta de IA y el idioma del TTS

## Arquitectura

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

## Requisitos

| Dependencia | Versión | Notas |
|:-----------|:-------:|-------|
| Python | 3.10+ | Runtime del servicio de IA |
| Java | 17+ | Runtime del backend de negocios |
| Maven | 3.8+ | Herramienta de build para Java |
| MySQL | 8.0+ | Almacenamiento relacional de datos |
| macOS (recomendado) | 13+ | `ocrmac` usa el framework Apple Vision para OCR |

> **Linux**: Compatible, pero requiere [Tesseract](https://github.com/tesseract-ocr/tesseract) para OCR. Instalar con `apt install tesseract-ocr tesseract-ocr-chi-sim` y modificar `backend-ai/services/ocr.py`.

## API Keys

Necesitas un **DeepSeek API Key** (obligatorio) y opcionalmente un **Groq API Key** (para el reconocimiento de voz en la Mini Program de WeChat).

<details>
<summary><strong>Cómo obtener un DeepSeek API Key (obligatorio)</strong></summary>

DeepSeek proporciona el LLM para responder preguntas.

1. Ve a [platform.deepseek.com](https://platform.deepseek.com/)
2. Regístrate o inicia sesión
3. Navega a **API Keys** en la barra lateral izquierda
4. Haz clic en **Create API Key**, asígnale un nombre (por ejemplo, "MedVision")
5. Copia la clave de inmediato (empieza con `sk-` y no se volverá a mostrar)

**Costo**: El modelo por defecto `deepseek-v4-flash` es extremadamente económico. Un día completo de pruebas de desarrollo suele costar menos de $0.01.

</details>

<details>
<summary><strong>Cómo obtener un Groq API Key (opcional — solo para Mini Program)</strong></summary>

Groq proporciona reconocimiento de voz rápido mediante Whisper Large-V3 en hardware LPU.

1. Ve a [console.groq.com](https://console.groq.com/)
2. Regístrate con tu cuenta de GitHub o Google
3. Navega a **API Keys** en la barra lateral izquierda
4. Haz clic en **Create API Key**
5. Copia la clave (empieza con `gsk-`)

**Costo**: El plan gratuito incluye un uso generoso de Whisper. El frontend web usa la API de voz incorporada del navegador y **no** consume créditos de Groq — solo la Mini Program de WeChat usa Groq.

</details>

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/Ha1baraA11/MedVision_RAG.git
cd MedVision_RAG
```

### 2. Configurar el entorno

```bash
cp .env.example .env
```

Abre `.env` en cualquier editor de texto y completa los valores:

```bash
# macOS
open -e .env

# VS Code
code .env
```

| Variable | Requerida | Descripción |
|----------|:--------:|-------------|
| `MYSQL_PASSWORD` | **Sí** | Tu contraseña root de MySQL |
| `DEEPSEEK_API_KEY` | **Sí** | Obtener en [platform.deepseek.com](https://platform.deepseek.com/) |
| `DEEPSEEK_BASE_URL` | No | Por defecto: `https://api.deepseek.com` |
| `GROQ_API_KEY` | Mini Program | Obtener en [console.groq.com](https://console.groq.com/) |
| `SMTP_SERVER` | No | Servidor SMTP para alertas de riesgo (ej. `smtp.qq.com`) |
| `SMTP_PORT` | No | Puerto SMTP (QQ Mail: `465`) |
| `SMTP_USER` | No | Dirección de correo del remitente |
| `SMTP_PASSWORD` | No | Código de autorización SMTP (no es tu contraseña de correo) |
| `SMTP_RECEIVER` | No | Dirección de correo del destinatario |
| `INTERNAL_TOKEN` | No | Token de autenticación entre servicios Java y Python |

> **Nota**: `MYSQL_PASSWORD` es la única credencial verdaderamente obligatoria para que el sistema inicie. Todo lo demás tiene valores predeterminados seguros o una degradación elegante.

<details>
<summary><strong>Cómo obtener el código de autorización SMTP de QQ Mail</strong></summary>

1. Inicia sesión en [mail.qq.com](https://mail.qq.com/) → Configuración → Cuenta
2. Busca **POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV Service**
3. Activa **IMAP/SMTP Service**
4. Sigue las instrucciones de verificación por SMS para obtener un **código de autorización**
5. Usa este código (no tu contraseña de QQ) como `SMTP_PASSWORD`

</details>

### 3. Configurar el entorno de Python

```bash
cd backend-ai

# Crear entorno virtual
python3 -m venv venv

# Activarlo
source venv/bin/activate

# Instalar dependencias (solo la primera vez, tarda ~2 min)
pip install -r requirements.txt
```

La primera ejecución descargará el modelo de embeddings `bge-small-zh-v1.5` (~90MB) desde HuggingFace.

### 4. Configurar el entorno de Java

```bash
cd backend-java

# Descargar dependencias y compilar (solo la primera vez, tarda ~3 min)
mvn clean install -DskipTests
```

### 5. Inicializar la base de datos

```bash
mysql -u root -p < sql/init.sql
```

Esto crea:
- La base de datos `medvision` (UTF8MB4)
- La tabla `medicines` — información y texto completo de medicamentos
- La tabla `chat_logs` — historial de conversaciones y analíticas
- La tabla `admin_users` — cuentas de administrador

La cuenta de administrador por defecto (`admin` / `admin`) se crea automáticamente cuando el backend de Java inicia por primera vez.

> **Alternativa**: Si omites este paso, el `hibernate.ddl-auto=update` de Spring Boot creará las tablas automáticamente al iniciar. El script SQL se proporciona para un manejo explícito del esquema y despliegues en producción.

## Uso

### Inicio rápido (todos los servicios a la vez)

```bash
./start_all.sh
```

Este script inicia todos los servicios en orden de dependencia, espera a que cada uno esté listo e imprime el estado. Los registros se escriben en `backend-ai/service.log`, `backend-java/backend.log` y `dashboard.log`.

### Inicio manual (3 terminales separadas)

**Terminal 1 — Servicio de IA en Python** (iniciar primero, es el más lento)

```bash
cd backend-ai
source venv/bin/activate
python main.py
```

Espera a que aparezca: `Uvicorn running on http://0.0.0.0:8001`

> En el primer inicio, el modelo de embeddings (`bge-small-zh-v1.5`) se descargará y quedará en caché. Los inicios posteriores tardan ~3 segundos.

**Terminal 2 — Backend de Java**

```bash
cd backend-java
mvn spring-boot:run
```

Espera a que aparezca: `Started MedVisionApplication in X.XXX seconds`

> Maven descarga las dependencias en la primera ejecución. El backend crea automáticamente las tablas de la base de datos y la cuenta de administrador por defecto.

**Terminal 3 — Frontend web**

```bash
cd frontend
python3 -m http.server 5174
```

Abre http://localhost:5174 en tu navegador.

**Opcional — Panel de administración**

```bash
streamlit run admin_dashboard.py --server.port 8502
```

Abre http://localhost:8502. Usuario: `admin` / `admin`.

### Detener todos los servicios

```bash
./stop_all.sh
```

O manualmente:

```bash
lsof -t -i:5174 -i:8080 -i:8001 -i:8502 | xargs kill -9
```

## Mini Program de WeChat

### Configuración

1. Descarga e instala [WeChat Developer Tools](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. Abre la herramienta y haz clic en **Import Project**
3. Selecciona el directorio `frontend-wechat/`
4. Elige **Test AppID** o el modo invitado
5. Edita `frontend-wechat/config.js`:

```js
const API_CANDIDATES = [
  'http://192.168.x.x:8080',  // reemplaza con la IP LAN de tu computadora
];
```

### Cómo encontrar tu IP de red local

```bash
# macOS
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr "IPv4"
```

### Depuración en dispositivo real

1. Asegúrate de que tu teléfono y tu computadora estén en la **misma red Wi-Fi**
2. En WeChat Developer Tools, haz clic en **Debug on Device**
3. Escanea el código QR con tu teléfono
4. Si la conexión falla, verifica:
   - Que el firewall de la computadora permita el puerto `8080`
   - Que `config.js` tenga la IP LAN correcta (no `localhost`)
   - Que el backend de Java esté ejecutándose

## Configuración

### Cambiar el modelo de LLM

Edita `backend-ai/core/config.py`:

```python
llm = ChatOpenAI(
    model="deepseek-v4-flash",   # cambia el modelo aquí
    api_key=API_KEY,
    base_url=BASE_URL,
    temperature=0.3               # 0.0 = determinista, 1.0 = creativo
)
```

Modelos disponibles de DeepSeek:
| Modelo | Velocidad | Costo | Recomendado para |
|-------|:-----:|:----:|-----------------|
| `deepseek-v4-flash` | Rápido | Muy bajo | Desarrollo, demostración (por defecto) |
| `deepseek-v4` | Medio | Bajo | Respuestas de mayor calidad |

### Motor OCR

`ocrmac` (macOS Vision) se usa por defecto. Para cambiar a Tesseract en Linux:

```bash
# Instalar Tesseract con soporte para chino
sudo apt install tesseract-ocr tesseract-ocr-chi-sim

# Instalar el wrapper de Python
pip install pytesseract
```

Luego modifica `backend-ai/services/ocr.py` para usar `pytesseract` en lugar de `ocrmac`.

### Modelo de embeddings

El modelo por defecto es `BAAI/bge-small-zh-v1.5` (optimizado para texto médico en chino, ~90MB). Se ejecuta localmente en CPU — no requiere llamadas a API. Para cambiarlo:

```python
# backend-ai/core/config.py
embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",  # cambia el modelo aquí
    model_kwargs={"local_files_only": True, "device": "cpu"}
)
```

> Cambia `local_files_only` a `False` en la primera ejecución para descargar desde HuggingFace.

### Palabras clave de riesgo

Edita `risk_keywords.json` para agregar o eliminar palabras de activación:

```json
{
  "keywords": ["过量", "中毒", "过敏", "禁忌", "副作用", "..."]
}
```

Cuando alguna palabra clave aparece en la pregunta del usuario o en la respuesta de la IA, el sistema registra el evento y (si está configurado) envía una alerta por correo.

### Seguridad del panel de administración

El panel de administración restringe el acceso mediante una lista blanca de IPs. Configúralo en `backend-java/src/main/resources/application.properties`:

```properties
admin.security.enabled=true
admin.security.ip-whitelist=127.0.0.1,::1
```

Agrega tu IP a la lista blanca si accedes de forma remota.

### Configuración inicial del modelo de embeddings

El modelo de embeddings se almacena en caché localmente después de la primera descarga. Si necesitas forzar una re-descarga:

```bash
cd backend-ai
source venv/bin/activate
python -c "from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='BAAI/bge-small-zh-v1.5')"
```

## Endpoints de API

### Servicio de IA en Python (`:8001`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Verificación de salud |
| `POST` | `/ocr` | OCR de imagen/PDF/Word → extraer texto |
| `POST` | `/chat` | Respuesta a preguntas con RAG |
| `POST` | `/transcribe` | Voz-a-texto (Whisper vía Groq) |
| `POST` | `/analyze` | Análisis manual de texto |
| `GET` | `/tts` | Texto-a-voz (edge-tts) |
| `GET` | `/search` | Buscar historial de medicamentos |

### Backend de Java (`:8080`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/medicine/health` | Verificación de salud |
| `POST` | `/api/medicine/recognize` | Subir y reconocer prospecto de medicamento |
| `POST` | `/api/medicine/chat` | Proxy al servicio de chat de IA |
| `GET` | `/api/medicine/list` | Listar todos los medicamentos almacenados |
| `GET` | `/api/medicine/chat-logs` | Historial de chats (admin) |
| `GET` | `/api/medicine/analytics` | Analíticas de uso (admin) |
| `POST` | `/api/medicine/admin/login` | Inicio de sesión de administrador |

## Pruebas

```bash
# Pruebas unitarias de Python (17 pruebas, ~0.2s)
cd backend-ai
source venv/bin/activate
python -m pytest tests/ -v

# Pruebas unitarias de Java (6 pruebas)
cd backend-java
mvn test
```

### Cobertura de pruebas

| Módulo | Pruebas | Cubre |
|--------|:-----:|-------|
| `check_risk_keywords` | 6 | Coincidencia, caché, expiración, entrada vacía |
| `smart_rag_search` | 4 | Texto corto, texto largo, respaldo ante error, casos límite |
| `correct_medical_terms` | 7 | Filtro de alucinaciones, lista negra, corrección por LLM, respaldo ante error |
| `MedicineController` | 6 | Pruebas MockMvc de endpoints REST |

## Estructura del proyecto

```
MedVision-RAG/
├── frontend/                  # Aplicación web de archivo único con Vue 3
│   └── index.html             # Frontend completo (848 líneas)
├── frontend-wechat/           # Mini Program de WeChat
│   ├── pages/index/           # Página principal (WXML + JS + WXSS)
│   ├── app.js                 # Punto de entrada de la app
│   └── config.js              # Configuración de endpoints de API
├── backend-java/              # Backend de negocios con Spring Boot
│   ├── src/main/java/com/medvision/
│   │   ├── controller/        # Endpoints REST
│   │   ├── service/           # Lógica de negocios
│   │   ├── entity/            # Entidades JPA (Medicine, ChatLog, AdminUser)
│   │   ├── repository/        # Repositorios de Spring Data JPA
│   │   └── config/            # Seguridad, CORS, lista blanca de IPs, inicialización de datos
│   ├── src/test/              # Pruebas MockMvc
│   └── pom.xml                # Dependencias Maven
├── backend-ai/                # Servicio de IA con FastAPI
│   ├── main.py                # Punto de entrada de rutas (~250 líneas)
│   ├── core/
│   │   ├── config.py          # Singleton globales (LLM, embeddings, cliente Groq)
│   │   ├── logging_config.py  # Logging estructurado + middleware de trazas
│   │   └── security.py        # Verificación de token interno
│   ├── services/
│   │   ├── ocr.py             # OCR (ocrmac + Tesseract como respaldo)
│   │   ├── asr.py             # Reconocimiento de voz (Groq Whisper)
│   │   ├── rag.py             # RAG adaptativo (context stuffing + búsqueda vectorial)
│   │   ├── tts.py             # Texto-a-voz (edge-tts)
│   │   ├── risk.py            # Detección de palabras clave de riesgo + caché TTL
│   │   ├── email.py           # Alerta de riesgo por correo (pool de hilos asíncrono)
│   │   ├── intent.py          # Análisis de intención (medicamento actual vs. historial)
│   │   ├── search.py          # Búsqueda en historial de medicamentos
│   │   └── chat_model.py      # Cambio de modelo de chat
│   ├── models/
│   │   └── schemas.py         # Modelos de solicitud con Pydantic
│   └── tests/                 # Pruebas unitarias con pytest
├── admin_dashboard.py         # Panel de administración con Streamlit
├── risk_keywords.json         # Diccionario de palabras clave de riesgo
├── sql/
│   └── init.sql               # Script de inicialización de la base de datos
├── Package-Insert_Test/       # Prospectos de ejemplo para pruebas
├── .env.example               # Plantilla de variables de entorno
├── .gitignore                 # Reglas de ignorado de Git
├── start_all.sh               # Script para iniciar todos los servicios
└── stop_all.sh                # Script para detener todos los servicios
```

## Preguntas frecuentes

### Instalación e inicio

**`No module named 'ocrmac'`**

`ocrmac` usa el framework Vision de macOS y solo funciona en macOS. Para Linux, instala Tesseract:

```bash
sudo apt install tesseract-ocr tesseract-ocr-chi-sim
pip install pytesseract
```

Luego modifica `backend-ai/services/ocr.py` para usar `pytesseract`.

**`Connection refused' al iniciar el backend de Java**

MySQL no está ejecutándose o la contraseña es incorrecta.

```bash
# Verificar el estado de MySQL
mysql -u root -p -e "SELECT 1"

# Confirmar que la contraseña en .env coincide con tu contraseña root de MySQL
cat .env | grep MYSQL_PASSWORD
```

**Advertencia de `torchaudio' al iniciar Python**

Es una advertencia no fatal sobre VAD (Voice Activity Detection). El sistema recurre al modo sin VAD y funciona correctamente. Para solucionarlo: `pip install torchaudio`.

**La descarga de Maven es lenta**

Agrega un mirror en `~/.m2/settings.xml`:

```xml
<mirrors>
  <mirror>
    <id>aliyun</id>
    <mirrorOf>central</mirrorOf>
    <url>https://maven.aliyun.com/repository/central</url>
  </mirror>
</mirrors>
```

### Uso

**Pantalla en blanco en el navegador**

Abre DevTools (F12) → pestaña Console. Causas comunes:
- El servicio de IA no se inició → verifica el puerto `8001`
- El backend de Java no se inició → verifica el puerto `8080`
- Error de CORS → asegúrate de acceder mediante `localhost:5174`, no `file://`

**La Mini Program no se conecta al backend**

1. Verifica que el teléfono y la computadora estén en la **misma red Wi-Fi**
2. Revisa que `config.js` tenga tu IP LAN (no `localhost` ni `127.0.0.1`)
3. Confirma que el firewall de tu computadora permita conexiones entrantes en el puerto `8080`
4. Prueba `curl http://TU_IP_LAN:8080/api/medicine/health` desde el navegador de tu teléfono

**El reconocimiento de voz no funciona (web)**

Los navegadores requieren HTTPS o `localhost` para acceder al micrófono. Asegúrate de acceder a la página mediante `http://localhost:5174`, no una IP de red local.

**El reconocimiento de voz no funciona (Mini Program)**

Verifica que `GROQ_API_KEY` esté configurado en `.env`. Reinicia el servicio de IA de Python después de modificar `.env`.

**El OCR devuelve "medicamento desconocido" o texto ilegible**

- Asegúrate de que la foto sea clara y esté bien iluminada
- El nombre del medicamento debe ser visible en la imagen
- Para PDFs, verifica si el archivo es una imagen escaneada (texto no buscable) — el sistema lo detectará automáticamente y usará OCR de imagen

### Base de datos

**¿Cómo restablecer la base de datos?**

```bash
mysql -u root -p -e "DROP DATABASE IF EXISTS medvision;"
mysql -u root -p < sql/init.sql
```

Luego reinicia el backend de Java para recrear la cuenta de administrador por defecto.

**¿Cómo cambiar la contraseña del administrador?**

Usa el panel de administración (http://localhost:8502) después de iniciar sesión, o actualízala directamente en MySQL:

```sql
USE medvision;
UPDATE admin_users SET password_hash = '$2a$10$...' WHERE username = 'admin';
```

Genera un hash BCrypt usando cualquier herramienta en línea o Python:

```python
from passlib.hash import bcrypt
print(bcrypt.hash("tu_nueva_contraseña"))
```

## Licencia

MIT
