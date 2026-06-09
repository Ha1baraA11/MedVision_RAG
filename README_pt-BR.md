<p align="center">
  <img src="assets/logo.png" alt="MedVision-RAG Logo" width="200">
</p>

<h1 align="center">MedVision-RAG</h1>

<p align="center">
  <strong>Assistente de medicamentos com IA e interacao por voz</strong><br>
  Fotografe qualquer bula de remedio e obtenha respostas instantaneas via RAG + voz.
</p>

<p align="center">
  <a href="README.md">English</a> · <a href="README_CN.md">简体中文</a> · <a href="README_TW.md">繁體中文</a> · <a href="README_ja.md">日本語</a> · <a href="README_ko.md">한국어</a> · <a href="README_es.md">Español</a> · <a href="README_ru.md">Русский</a> · <a href="README_fr.md">Français</a> · <a href="README_de.md">Deutsch</a>
</p>

---

## O que faz

O MedVision-RAG ajuda usuarios com deficiencia visual e idosos a entenderem seus medicamentos. Aponte a camera para a embalagem de um remedio ou envie um arquivo PDF/Word, e o sistema:

1. **Extrai o texto** via OCR (macOS Vision / Tesseract como alternativa)
2. **Limpa o texto** usando o pipeline do Unstructured.io (espacos em branco, paragrafos quebrados, marcadores)
3. **Constroi uma base de conhecimento** vetorizando o texto no ChromaDB
4. **Responde perguntas** usando RAG adaptativo — textos curtos usam context stuffing direto, textos longos usam busca por similaridade vetorial
5. **Le a resposta em voz alta** via edge-tts

O sistema suporta **navegador web**, **Mini Program do WeChat** e um **painel administrativo** para monitoramento de logs de conversas e analises.

## Funcionalidades

### OCR multi-formato
- **Fotos**: Embalagens, caixas, blisters — diretamente pela camera
- **PDF**: Tanto baseado em texto quanto escaneado (detecta automaticamente e renderiza como imagem para OCR)
- **Word**: Extrai texto e tabelas; recorre a OCR de imagens embutidas quando o texto e insuficiente
- **HEIC/HEIF**: Fotos do iPhone sao convertidas automaticamente para JPEG antes do OCR

### Motor RAG adaptativo
- **Texto curto** (< 1500 caracteres): Context Stuffing — injeta o documento completo no prompt do LLM
- **Texto longo** (>= 1500 caracteres): Busca vetorial — divide em fragmentos, armazena no ChromaDB, recupera os trechos mais relevantes (top-K)
- **Troca entre medicamentos**: Quando o usuario menciona outro remedio pelo nome, o sistema troca o contexto automaticamente

### Interacao por voz
- **Web**: API de reconhecimento de fala nativa do navegador (latencia zero, sem custo de API)
- **Mini Program**: Groq Whisper Large-V3 para fala-para-texto, edge-tts para texto-para-fala
- **Correcao de termos medicos**: O LLM pos-processa a saida do ASR para corrigir nomes de medicamentos reconhecidos incorretamente
- **Reproducao interrompivel**: Pressione o botao de fala para interromper imediatamente o TTS em andamento

### Monitoramento de riscos
- **Deteccao por palavras-chave**: Palavras-chave de risco configuraveis em `risk_keywords.json`
- **Auditoria de logs**: Todas as conversas sao armazenadas no MySQL para revisao
- **Alertas por e-mail**: Notificacao automatica por e-mail quando palavras-chave de risco sao acionadas (configuravel)
- **Painel administrativo**: Monitoramento em tempo real via Streamlit com protecao por whitelist de IP

### Acessibilidade
- UI de alto contraste (compativel com WCAG AA)
- Alvos de toque grandes (48px+)
- Fluxo de trabalho totalmente conduzido por voz para usuarios com deficiencia visual
- Alternancia entre chines/ingles com sincronizacao do idioma da resposta da IA e do TTS

## Arquitetura

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

| Dependencia | Versao | Observacoes |
|:-----------|:-------:|-------|
| Python | 3.10+ | Runtime do servico de IA |
| Java | 17+ | Runtime do backend de negocios |
| Maven | 3.8+ | Ferramenta de build Java |
| MySQL | 8.0+ | Armazenamento relacional de dados |
| macOS (recomendado) | 13+ | `ocrmac` usa o framework Apple Vision para OCR |

> **Linux**: Suportado, mas requer [Tesseract](https://github.com/tesseract-ocr/tesseract) para OCR. Instale via `apt install tesseract-ocr tesseract-ocr-chi-sim` e modifique `backend-ai/services/ocr.py`.

## Chaves de API

Voce precisa de uma **DeepSeek API Key** (obrigatoria) e opcionalmente de uma **Groq API Key** (para reconhecimento de fala no Mini Program do WeChat).

<details>
<summary><strong>Como obter a DeepSeek API Key (obrigatoria)</strong></summary>

A DeepSeek fornece o LLM para responder perguntas.

1. Acesse [platform.deepseek.com](https://platform.deepseek.com/)
2. Crie uma conta ou faca login
3. Navegue ate **API Keys** no menu lateral esquerdo
4. Clique em **Create API Key**, de um nome (ex.: "MedVision")
5. Copie a chave imediatamente (comeca com `sk-` e nao sera exibida novamente)

**Custo**: O modelo padrao `deepseek-v4-flash` e extremamente barato. Um dia inteiro de testes de desenvolvimento normalmente custa menos de $0.01.

</details>

<details>
<summary><strong>Como obter a Groq API Key (opcional — apenas Mini Program)</strong></summary>

A Groq oferece fala-para-texto rapida via Whisper Large-V3 em hardware LPU.

1. Acesse [console.groq.com](https://console.groq.com/)
2. Crie uma conta com GitHub ou Google
3. Navegue ate **API Keys** no menu lateral esquerdo
4. Clique em **Create API Key**
5. Copie a chave (comeca com `gsk-`)

**Custo**: O plano gratuito inclui uso generoso do Whisper. O frontend web usa a API de fala nativa do navegador e **nao** consome creditos Groq — apenas o Mini Program do WeChat usa Groq.

</details>

## Instalacao

### 1. Clonar

```bash
git clone https://github.com/Ha1baraA11/MedVision_RAG.git
cd MedVision_RAG
```

### 2. Configurar ambiente

```bash
cp .env.example .env
```

Abra o `.env` em qualquer editor de texto e preencha com seus valores:

```bash
# macOS
open -e .env

# VS Code
code .env
```

| Variavel | Obrigatoria | Descricao |
|----------|:--------:|-------------|
| `MYSQL_PASSWORD` | **Sim** | Sua senha root do MySQL |
| `DEEPSEEK_API_KEY` | **Sim** | Obtenha em [platform.deepseek.com](https://platform.deepseek.com/) |
| `DEEPSEEK_BASE_URL` | Nao | Padrao: `https://api.deepseek.com` |
| `GROQ_API_KEY` | Mini Program | Obtenha em [console.groq.com](https://console.groq.com/) |
| `SMTP_SERVER` | Nao | Servidor SMTP para alertas de risco (ex.: `smtp.qq.com`) |
| `SMTP_PORT` | Nao | Porta SMTP (QQ Mail: `465`) |
| `SMTP_USER` | Nao | Endereco de e-mail do remetente |
| `SMTP_PASSWORD` | Nao | Codigo de autorizacao SMTP (nao e a senha do e-mail) |
| `SMTP_RECEIVER` | Nao | Endereco de e-mail do destinatario |
| `INTERNAL_TOKEN` | Nao | Token de autenticacao entre os servicos Java ↔ Python |

> **Observacao**: `MYSQL_PASSWORD` e a unica credencial realmente obrigatoria para o sistema iniciar. Todo o resto tem valores padrao seguros ou degradacao graciosa.

<details>
<summary><strong>Como obter o codigo de autorizacao SMTP do QQ Mail</strong></summary>

1. Faca login em [mail.qq.com](https://mail.qq.com/) → Configuracoes → Conta
2. Encontre **POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV Service**
3. Ative o **Servico IMAP/SMTP**
4. Siga a verificacao por SMS para obter um **codigo de autorizacao**
5. Use este codigo (nao a senha do QQ) como `SMTP_PASSWORD`

</details>

### 3. Configurar ambiente Python

```bash
cd backend-ai

# Criar ambiente virtual
python3 -m venv venv

# Ativar
source venv/bin/activate

# Instalar dependencias (primeira vez apenas, leva ~2 min)
pip install -r requirements.txt
```

A primeira execucao fara o download do modelo de embeddings `bge-small-zh-v1.5` (~90MB) do HuggingFace.

### 4. Configurar ambiente Java

```bash
cd backend-java

# Baixar dependencias e compilar (primeira vez apenas, leva ~3 min)
mvn clean install -DskipTests
```

### 5. Inicializar banco de dados

```bash
mysql -u root -p < sql/init.sql
```

Isso cria:
- Banco de dados `medvision` (UTF8MB4)
- Tabela `medicines` — informacoes e texto completo dos medicamentos
- Tabela `chat_logs` — historico de conversas e analises
- Tabela `admin_users` — contas de administrador

A conta de administrador padrao (`admin` / `admin`) e criada automaticamente quando o backend Java e iniciado pela primeira vez.

> **Alternativa**: Se voce pular esta etapa, o `hibernate.ddl-auto=update` do Spring Boot criara as tabelas automaticamente na inicializacao. O script SQL e fornecido para gerenciamento explicito do esquema e implantacoes em producao.

## Uso

### Inicio rapido (todos os servicos de uma vez)

```bash
./start_all.sh
```

Este script inicia todos os servicos em ordem de dependencia, aguarda cada um ficar pronto e exibe o status. Os logs sao gravados em `backend-ai/service.log`, `backend-java/backend.log` e `dashboard.log`.

### Inicio manual (3 terminais separados)

**Terminal 1 — Servico de IA Python** (inicie primeiro, e o mais lento)

```bash
cd backend-ai
source venv/bin/activate
python main.py
```

Aguarde: `Uvicorn running on http://0.0.0.0:8001`

> Na primeira inicializacao, o modelo de embeddings (`bge-small-zh-v1.5`) sera baixado e armazenado em cache. As inicializacoes subsequentes levam ~3 segundos.

**Terminal 2 — Backend Java**

```bash
cd backend-java
mvn spring-boot:run
```

Aguarde: `Started MedVisionApplication in X.XXX seconds`

> O Maven baixa as dependencias na primeira execucao. O backend cria automaticamente as tabelas do banco de dados e a conta de administrador padrao.

**Terminal 3 — Frontend Web**

```bash
cd frontend
python3 -m http.server 5174
```

Abra http://localhost:5174 no seu navegador.

**Opcional — Painel Administrativo**

```bash
streamlit run admin_dashboard.py --server.port 8502
```

Abra http://localhost:8502. Login: `admin` / `admin`.

### Parar todos os servicos

```bash
./stop_all.sh
```

Ou manualmente:

```bash
lsof -t -i:5174 -i:8080 -i:8001 -i:8502 | xargs kill -9
```

## Mini Program do WeChat

### Configuracao

1. Baixe e instale o [WeChat Developer Tools](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. Abra a ferramenta, clique em **Import Project**
3. Selecione o diretorio `frontend-wechat/`
4. Escolha **Test AppID** ou modo convidado
5. Edite `frontend-wechat/config.js`:

```js
const API_CANDIDATES = [
  'http://192.168.x.x:8080',  // substitua pelo IP da rede local do seu computador
];
```

### Descobrindo seu IP de rede local

```bash
# macOS
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr "IPv4"
```

### Depuracao em dispositivo real

1. Certifique-se de que seu celular e computador estao na **mesma rede Wi-Fi**
2. No WeChat Developer Tools, clique em **Debug on Device**
3. Escaneie o QR code com seu celular
4. Se a conexao falhar, verifique:
   - O firewall do computador permite a porta `8080`
   - O `config.js` tem o IP de rede local correto (nao `localhost`)
   - O backend Java esta em execucao

## Configuracao

### Trocar o modelo de LLM

Edite `backend-ai/core/config.py`:

```python
llm = ChatOpenAI(
    model="deepseek-v4-flash",   # troque o modelo aqui
    api_key=API_KEY,
    base_url=BASE_URL,
    temperature=0.3               # 0.0 = deterministico, 1.0 = criativo
)
```

Modelos DeepSeek disponiveis:
| Modelo | Velocidade | Custo | Recomendado para |
|-------|:-----:|:----:|-----------------|
| `deepseek-v4-flash` | Rapido | Muito baixo | Desenvolvimento, demonstracao (padrao) |
| `deepseek-v4` | Medio | Baixo | Respostas de melhor qualidade |

### Motor OCR

`ocrmac` (macOS Vision) e usado por padrao. Para trocar para Tesseract no Linux:

```bash
# Instalar Tesseract com suporte a chines
sudo apt install tesseract-ocr tesseract-ocr-chi-sim

# Instalar wrapper Python
pip install pytesseract
```

Em seguida, modifique `backend-ai/services/ocr.py` para usar `pytesseract` em vez de `ocrmac`.

### Modelo de embeddings

O modelo padrao e `BAAI/bge-small-zh-v1.5` (otimizado para texto medico em chines, ~90MB). Executa localmente na CPU — sem chamadas de API. Para alterar:

```python
# backend-ai/core/config.py
embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",  # troque o modelo aqui
    model_kwargs={"local_files_only": True, "device": "cpu"}
)
```

> Altere `local_files_only` para `False` na primeira uso para baixar do HuggingFace.

### Palavras-chave de risco

Edite `risk_keywords.json` para adicionar ou remover palavras de alerta:

```json
{
  "keywords": ["过量", "中毒", "过敏", "禁忌", "副作用", "..."]
}
```

Quando qualquer palavra-chave aparece na pergunta do usuario ou na resposta da IA, o sistema registra o evento e (se configurado) envia um alerta por e-mail.

### Seguranca do painel administrativo

O painel administrativo restringe o acesso por whitelist de IP. Configure em `backend-java/src/main/resources/application.properties`:

```properties
admin.security.enabled=true
admin.security.ip-whitelist=127.0.0.1,::1
```

Adicione seu IP a whitelist se acessar remotamente.

### Configuracao inicial do modelo de embeddings

O modelo de embeddings e armazenado em cache localmente apos o primeiro download. Se precisar forcar um novo download:

```bash
cd backend-ai
source venv/bin/activate
python -c "from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='BAAI/bge-small-zh-v1.5')"
```

## Endpoints da API

### Servico de IA Python (`:8001`)

| Metodo | Caminho | Descricao |
|--------|------|-------------|
| `GET` | `/health` | Verificacao de saude |
| `POST` | `/ocr` | OCR de imagem/PDF/Word → extrair texto |
| `POST` | `/chat` | Resposta a perguntas via RAG |
| `POST` | `/transcribe` | Fala-para-texto (Whisper via Groq) |
| `POST` | `/analyze` | Analise manual de texto |
| `GET` | `/tts` | Texto-para-fala (edge-tts) |
| `GET` | `/search` | Buscar historico de medicamentos |

### Backend Java (`:8080`)

| Metodo | Caminho | Descricao |
|--------|------|-------------|
| `GET` | `/api/medicine/health` | Verificacao de saude |
| `POST` | `/api/medicine/recognize` | Enviar e reconhecer bula de remedio |
| `POST` | `/api/medicine/chat` | Proxy para o chat do servico de IA |
| `GET` | `/api/medicine/list` | Listar todos os medicamentos armazenados |
| `GET` | `/api/medicine/chat-logs` | Historico de logs de conversas (admin) |
| `GET` | `/api/medicine/analytics` | Analises de uso (admin) |
| `POST` | `/api/medicine/admin/login` | Login do administrador |

## Testes

```bash
# Testes unitarios Python (17 testes, ~0.2s)
cd backend-ai
source venv/bin/activate
python -m pytest tests/ -v

# Testes unitarios Java (6 testes)
cd backend-java
mvn test
```

### Cobertura de testes

| Modulo | Testes | Cobertura |
|--------|:-----:|--------|
| `check_risk_keywords` | 6 | Acerto, cache, expiracao, entrada vazia |
| `smart_rag_search` | 4 | Texto curto, texto longo, fallback de erro, casos extremos |
| `correct_medical_terms` | 7 | Filtro de alucinacao, lista negra, correcao por LLM, fallback de erro |
| `MedicineController` | 6 | Testes MockMvc de endpoints REST |

## Estrutura do projeto

```
MedVision-RAG/
├── frontend/                  # Aplicacao web Vue 3 em arquivo unico
│   └── index.html             # Frontend completo (848 linhas)
├── frontend-wechat/           # Mini Program do WeChat
│   ├── pages/index/           # Pagina principal (WXML + JS + WXSS)
│   ├── app.js                 # Entrada do app
│   └── config.js              # Configuracao do endpoint da API
├── backend-java/              # Backend de negocios Spring Boot
│   ├── src/main/java/com/medvision/
│   │   ├── controller/        # Endpoints REST
│   │   ├── service/           # Logica de negocios
│   │   ├── entity/            # Entidades JPA (Medicine, ChatLog, AdminUser)
│   │   ├── repository/        # Repositorios Spring Data JPA
│   │   └── config/            # Seguranca, CORS, whitelist de IP, inicializacao de dados
│   ├── src/test/              # Testes MockMvc
│   └── pom.xml                # Dependencias Maven
├── backend-ai/                # Servico de IA FastAPI
│   ├── main.py                # Entrada das rotas (~250 linhas)
│   ├── core/
│   │   ├── config.py          # Singletons globais (LLM, embedding, cliente Groq)
│   │   ├── logging_config.py  # Logging estruturado + middleware de trace
│   │   └── security.py        # Verificacao de token interno
│   ├── services/
│   │   ├── ocr.py             # OCR (ocrmac + Tesseract como alternativa)
│   │   ├── asr.py             # Reconhecimento de fala (Groq Whisper)
│   │   ├── rag.py             # RAG adaptativo (context stuffing + busca vetorial)
│   │   ├── tts.py             # Texto-para-fala (edge-tts)
│   │   ├── risk.py            # Deteccao de palavras-chave de risco + cache TTL
│   │   ├── email.py           # E-mail de alerta de risco (pool de threads assincrono)
│   │   ├── intent.py          # Analise de intencao (medicamento atual vs historico)
│   │   ├── search.py          # Busca no historico de medicamentos
│   │   └── chat_model.py      # Troca de modelo de chat
│   ├── models/
│   │   └── schemas.py         # Modelos de requisicao Pydantic
│   └── tests/                 # Testes unitarios pytest
├── admin_dashboard.py         # Painel administrativo Streamlit
├── risk_keywords.json         # Dicionario de palavras-chave de risco
├── sql/
│   └── init.sql               # Script de inicializacao do banco de dados
├── Package-Insert_Test/       # Exemplos de bulas para teste
├── .env.example               # Template de variaveis de ambiente
├── .gitignore                 # Regras de ignorar do Git
├── start_all.sh               # Iniciar todos os servicos com um comando
└── stop_all.sh                # Parar todos os servicos com um comando
```

## Perguntas frequentes

### Instalacao e inicializacao

**`No module named 'ocrmac'`**

O `ocrmac` usa o framework macOS Vision e so funciona no macOS. Para Linux, instale o Tesseract:

```bash
sudo apt install tesseract-ocr tesseract-ocr-chi-sim
pip install pytesseract
```

Em seguida, modifique `backend-ai/services/ocr.py` para usar `pytesseract`.

**`Connection refused` ao iniciar o backend Java**

O MySQL nao esta em execucao ou a senha esta incorreta.

```bash
# Verificar status do MySQL
mysql -u root -p -e "SELECT 1"

# Verificar se a senha do .env corresponde a senha root do MySQL
cat .env | grep MYSQL_PASSWORD
```

**Aviso do `torchaudio` ao iniciar o Python**

E um aviso nao fatal sobre VAD (Voice Activity Detection). O sistema recorre ao modo sem VAD e funciona normalmente. Para corrigir: `pip install torchaudio`.

**Download do Maven e lento**

Adicione um mirror ao `~/.m2/settings.xml`:

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

**Tela branca no navegador**

Abra o DevTools (F12) → aba Console. Causas comuns:
- Servico de IA nao iniciado → verifique a porta `8001`
- Backend Java nao iniciado → verifique a porta `8080`
- Erro de CORS → certifique-se de acessar via `localhost:5174`, nao `file://`

**Mini Program nao consegue conectar ao backend**

1. Verifique se o celular e o computador estao na **mesma rede Wi-Fi**
2. Verifique se o `config.js` tem o IP de rede local correto (nao `localhost` nem `127.0.0.1`)
3. Verifique se o firewall do computador permite conexoes de entrada na porta `8080`
4. Tente `curl http://SEU_IP_LOCAL:8080/api/medicine/health` pelo navegador do celular

**Reconhecimento de fala nao funciona (web)**

Os navegadores exigem HTTPS ou `localhost` para acesso ao microfone. Certifique-se de acessar a pagina via `http://localhost:5174`, nao por um IP de rede local.

**Reconhecimento de fala nao funciona (Mini Program)**

Verifique se `GROQ_API_KEY` esta definida no `.env`. Reinicie o servico de IA Python apos alterar o `.env`.

**OCR retorna "medicamento desconhecido" ou texto ilegivel**

- Certifique-se de que a foto esta nitida e bem iluminada
- O nome do medicamento deve estar visivel na imagem
- Para PDFs, verifique se o arquivo e uma imagem escaneada (nao texto pesquisavel) — o sistema detectara automaticamente e usara OCR de imagem

### Banco de dados

**Como redefinir o banco de dados**

```bash
mysql -u root -p -e "DROP DATABASE IF EXISTS medvision;"
mysql -u root -p < sql/init.sql
```

Em seguida, reinicie o backend Java para recriar a conta de administrador padrao.

**Como alterar a senha do administrador**

Use o Painel Administrativo (http://localhost:8502) apos fazer login, ou atualize diretamente no MySQL:

```sql
USE medvision;
UPDATE admin_users SET password_hash = '$2a$10$...' WHERE username = 'admin';
```

Gere um hash BCrypt usando qualquer ferramenta online ou Python:

```python
from passlib.hash import bcrypt
print(bcrypt.hash("sua_nova_senha"))
```

## Licenca

MIT
