<p align="center">
  <img src="assets/logo.png" alt="MedVision-RAG Logo" width="200">
</p>

<h1 align="center">MedVision-RAG</h1>

<p align="center">
  <strong>Assistant medicamenteux propulse par l'IA avec interaction vocale</strong><br>
  Scannez un emballage de medicament ou importez une notice, puis obtenez des reponses fondees sur les documents, a l'oral ou par texte.
</p>

<p align="center">
    <a href="README.md">English</a> · <a href="README_CN.md">简体中文</a> · <a href="README_TW.md">繁體中文</a> · <a href="README_ja.md">日本語</a> · <a href="README_ko.md">한국어</a> · <a href="README_es.md">Español</a> · <a href="README_pt-BR.md">Português</a> · <a href="README_ru.md">Русский</a> · <a href="README_de.md">Deutsch</a>
</p>

---

## Ce que fait le projet

MedVision-RAG aide les utilisateurs malvoyants et les personnes agees a comprendre leurs medicaments. Pointez votre camera vers un emballage de medicament ou importez un document PDF/Word, et le systeme :

1. **Extrait le texte** via OCR (macOS Vision / Tesseract en secours)
2. **Normalise le texte OCR** tout en preservant une structure de paragraphes utile
3. **Construit une base de connaissances** en vectorisant le texte dans ChromaDB
4. **Repond aux questions** grace au RAG adaptatif — les textes courts utilisent l'injection directe du contexte, les textes longs utilisent la recherche par similarite vectorielle
5. **Lit la reponse a voix haute** via edge-tts

Le systeme prend en charge un **navigateur web**, un **mini-programme WeChat** et un **tableau de bord d'administration** pour la surveillance des journaux de discussion et des analyses.

## Fonctionnalites

### OCR multi-format
- **Photos** : emballages de medicaments, boites, plaquettes — directement via la camera
- **PDF** : texte et numérises (detection automatique et rendu en image pour l'OCR)
- **Word** : extraction du texte et des tableaux ; secours par OCR des images integrees lorsque le texte est insuffisant
- **HEIC/HEIF** : les photos iPhone sont converties automatiquement en JPEG avant l'OCR

### Moteur RAG adaptatif
- **Texte court** (< 1500 caracteres) : Context Stuffing — injection du document complet dans le prompt du LLM
- **Texte long** (>= 1500 caracteres) : recherche vectorielle — decoupage en morceaux, stockage dans ChromaDB, recuperation des passages pertinents les plus proches (top-K)
- **Changement de medicament** : lorsque l'utilisateur mentionne un medicament different par son nom, le systeme change automatiquement de contexte

### Interaction vocale
- **Web** : API de reconnaissance vocale native du navigateur (latence zero, aucun cout API)
- **Mini-programme** : Groq Whisper Large-V3 pour la parole-vers-texte, edge-tts pour la texte-vers-parole
- **Correction des termes medicaux** : le LLM post-traite la sortie ASR pour corriger les noms de medicaments mal reconnus
- **Lecture interruptible** : appuyez sur le bouton vocal pour arreter immediatement la lecture TTS en cours

### Surveillance des risques
- **Detection de mots-cles** : mots-cles de risque configurables dans `risk_keywords.json`
- **Audit des journaux de discussion** : toutes les conversations stockees dans MySQL pour examen
- **Alertes par e-mail** : notification automatique par e-mail lors du declenchement de mots-cles de risque (configurable)
- **Tableau de bord d'administration** : surveillance en temps reel via Streamlit avec protection par liste blanche IP

### Accessibilite
- Interface a contraste eleve (conforme WCAG AA)
- Cibles tactiles larges (48px+)
- Flux de travail entierement vocal pour les utilisateurs malvoyants
- Basculement chinois/anglais avec synchronisation de la reponse IA et de la selection de voix TTS

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

## Pre-requis

| Dependances | Version | Remarques |
|:-----------|:-------:|-------|
| Python | 3.10+ | Environnement d'execution du service IA |
| Java | 17+ | Environnement d'execution du backend metier |
| Maven | 3.8+ | Outil de build Java |
| MySQL | 8.0+ | Stockage relationnel de donnees |
| macOS (recommande) | 13+ | `ocrmac` utilise le framework Apple Vision pour l'OCR |

> **Linux** : pris en charge, mais necessite [Tesseract](https://github.com/tesseract-ocr/tesseract) pour l'OCR. Installez via `apt install tesseract-ocr tesseract-ocr-chi-sim` et modifiez `backend-ai/services/ocr.py`.

## Cles API

Vous avez besoin d'une **cle API DeepSeek** (obligatoire) et optionnellement d'une **cle API Groq** (pour la reconnaissance vocale du mini-programme WeChat).

<details>
<summary><strong>Comment obtenir une cle API DeepSeek (obligatoire)</strong></summary>

DeepSeek fournit le LLM pour la reponse aux questions.

1. Rendez-vous sur [platform.deepseek.com](https://platform.deepseek.com/)
2. Inscrivez-vous ou connectez-vous
3. Accedez a **API Keys** dans la barre laterale gauche
4. Cliquez sur **Create API Key** et donnez-lui un nom (par ex. « MedVision »)
5. Copiez la cle immediatement (elle commence par `sk-` et ne sera plus jamais affichee)

**Cout** : le modele par defaut `deepseek-v4-flash` est extremement economique. Une journee complete de tests de developpement coute generalement < 0,01 $.

</details>

<details>
<summary><strong>Comment obtenir une cle API Groq (optionnel — mini-programme uniquement)</strong></summary>

Groq offre une conversion parole-vers-texte rapide via Whisper Large-V3 sur du materiel LPU.

1. Rendez-vous sur [console.groq.com](https://console.groq.com/)
2. Inscrivez-vous avec un compte GitHub ou Google
3. Accedez a **API Keys** dans la barre laterale gauche
4. Cliquez sur **Create API Key**
5. Copiez la cle (commence par `gsk-`)

**Cout** : le forfait gratuit inclut une utilisation genereuse de Whisper. Le frontend web utilise l'API vocale integree au navigateur et ne **consomme pas** de credits Groq — seul le mini-programme WeChat utilise Groq.

</details>

## Installation

### 1. Cloner le depot

```bash
git clone https://github.com/Ha1baraA11/MedVision_RAG.git
cd MedVision_RAG
```

### 2. Configurer l'environnement

```bash
cp .env.example .env
```

Ouvrez `.env` dans un editeur de texte et remplissez vos valeurs :

```bash
# macOS
open -e .env

# VS Code
code .env
```

| Variable | Obligatoire | Description |
|----------|:--------:|-------------|
| `MYSQL_PASSWORD` | **Oui** | Votre mot de passe root MySQL |
| `DEEPSEEK_API_KEY` | **Oui** | Depuis [platform.deepseek.com](https://platform.deepseek.com/) |
| `DEEPSEEK_BASE_URL` | Non | Par defaut : `https://api.deepseek.com` |
| `GROQ_API_KEY` | Mini-programme | Depuis [console.groq.com](https://console.groq.com/) |
| `SMTP_SERVER` | Non | Serveur SMTP pour les alertes de risque (par ex. `smtp.qq.com`) |
| `SMTP_PORT` | Non | Port SMTP (QQ Mail : `465`) |
| `SMTP_USER` | Non | Adresse e-mail de l'expediteur |
| `SMTP_PASSWORD` | Non | Code d'autorisation SMTP (pas votre mot de passe e-mail) |
| `SMTP_RECEIVER` | Non | Adresse e-mail du destinataire |
| `INTERNAL_TOKEN` | Non | Jeton d'authentification entre les services Java et Python |

> **Remarque** : `MYSQL_PASSWORD` est la seule credentielle veritablement obligatoire pour le demarrage du systeme. Tout le reste possede des valeurs par defaut securisees ou une degradation gracieuse.

<details>
<summary><strong>Comment obtenir le code d'autorisation SMTP de QQ Mail</strong></summary>

1. Connectez-vous sur [mail.qq.com](https://mail.qq.com/) → Parametres → Compte
2. Trouvez **POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV Service**
3. Activez **IMAP/SMTP Service**
4. Suivez l'invite de verification par SMS pour obtenir un **code d'autorisation**
5. Utilisez ce code (pas votre mot de passe QQ) comme `SMTP_PASSWORD`

</details>

### 3. Configurer l'environnement Python

```bash
cd backend-ai

# Creer l'environnement virtuel
python3 -m venv venv

# L'activer
source venv/bin/activate

# Installer les dependances (premiere fois uniquement, ~2 min)
pip install -r requirements.txt
```

Le premier lancement telechargera le modele d'embedding `bge-small-zh-v1.5` (~90 Mo) depuis HuggingFace.

### 4. Configurer l'environnement Java

```bash
cd backend-java

# Telecharger les dependances et compiler (premiere fois uniquement, ~3 min)
mvn clean install -DskipTests
```

### 5. Initialiser la base de donnees

```bash
mysql -u root -p < sql/init.sql
```

Cela cree :
- La base de donnees `medvision` (UTF8MB4)
- La table `medicines` — informations sur les medicaments et texte integral
- La table `chat_logs` — historique des conversations et analyses
- La table `admin_users` — comptes administrateurs

Le compte administrateur par defaut (`admin` / `admin`) est cree automatiquement lors du premier demarrage du backend Java.

> **Alternative** : si vous sautez cette etape, le `hibernate.ddl-auto=update` de Spring Boot creera automatiquement les tables au demarrage. Le script SQL est fourni pour une gestion explicite du schema et les deploiements en production.

## Utilisation

### Demarrage rapide (tous les services en une fois)

```bash
./start_all.sh
```

Ce script demarre tous les services dans l'ordre de dependance, attend que chacun soit pret et affiche l'etat. Les journaux sont ecrits dans `backend-ai/service.log`, `backend-java/backend.log` et `dashboard.log`.

### Demarrage manuel (3 terminaux separes)

**Terminal 1 — Service IA Python** (demarrer en premier, c'est le plus lent)

```bash
cd backend-ai
source venv/bin/activate
python main.py
```

Attendre : `Uvicorn running on http://0.0.0.0:8001`

> Au premier demarrage, le modele d'embedding (`bge-small-zh-v1.5`) sera telecharge et mis en cache. Les demarrages suivants prennent environ 3 secondes.

**Terminal 2 — Backend Java**

```bash
cd backend-java
mvn spring-boot:run
```

Attendre : `Started MedVisionApplication in X.XXX seconds`

> Maven telecharge les dependances au premier lancement. Le backend cree automatiquement les tables de la base de donnees et le compte administrateur par defaut.

**Terminal 3 — Frontend Web**

```bash
cd frontend
python3 -m http.server 5174
```

Ouvrez http://localhost:5174 dans votre navigateur.

**Optionnel — Tableau de bord d'administration**

```bash
streamlit run admin_dashboard.py --server.port 8502
```

Ouvrez http://localhost:8502. Identifiants : `admin` / `admin`.

### Arreter tous les services

```bash
./stop_all.sh
```

Ou manuellement :

```bash
lsof -t -i:5174 -i:8080 -i:8001 -i:8502 | xargs kill -9
```

## Mini-programme WeChat

### Configuration

1. Telechargez et installez [WeChat Developer Tools](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. Ouvrez l'outil, cliquez sur **Import Project**
3. Selectionnez le repertoire `frontend-wechat/`
4. Choisissez **Test AppID** ou le mode invite
5. Editez `frontend-wechat/config.js` :

```js
const API_CANDIDATES = [
  'http://192.168.x.x:8080',  // remplacez par l'IP locale de votre ordinateur
];
```

### Trouver votre IP locale

```bash
# macOS
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr "IPv4"
```

### Debogage sur appareil reel

1. Assurez-vous que votre telephone et votre ordinateur sont sur le **même reseau Wi-Fi**
2. Dans WeChat Developer Tools, cliquez sur **Debug on Device**
3. Scannez le QR code avec votre telephone
4. Si la connexion echoue, verifiez :
   - Le pare-feu de l'ordinateur autorise le port `8080`
   - `config.js` contient la bonne IP locale (pas `localhost`)
   - Le backend Java est en cours d'execution

## Configuration

### Changer de modele LLM

Editez `backend-ai/core/config.py` :

```python
llm = ChatOpenAI(
    model="deepseek-v4-flash",   # changez le modele ici
    api_key=API_KEY,
    base_url=BASE_URL,
    temperature=0.3               # 0.0 = deterministe, 1.0 = creatif
)
```

Modeles DeepSeek disponibles :
| Modele | Vitesse | Cout | Recommande pour |
|-------|:-----:|:----:|-----------------|
| `deepseek-v4-flash` | Rapide | Tres faible | Developpement, demo (par defaut) |
| `deepseek-v4` | Moyen | Faible | Reponses de meilleure qualite |

### Moteur OCR

`ocrmac` (macOS Vision) est utilise par defaut. Pour basculer vers Tesseract sur Linux :

```bash
# Installer Tesseract avec le support chinois
sudo apt install tesseract-ocr tesseract-ocr-chi-sim

# Installer le wrapper Python
pip install pytesseract
```

Puis modifiez `backend-ai/services/ocr.py` pour utiliser `pytesseract` au lieu de `ocrmac`.

### Modele d'embedding

Le modele par defaut est `BAAI/bge-small-zh-v1.5` (optimise pour le texte medical chinois, ~90 Mo). Il s'execute localement sur CPU — aucun appel API necessaire. Pour le changer :

```python
# backend-ai/core/config.py
embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",  # changez le modele ici
    model_kwargs={"local_files_only": True, "device": "cpu"}
)
```

> Changez `local_files_only` a `False` lors de la premiere utilisation pour telecharger depuis HuggingFace.

### Mots-cles de risque

Editez `risk_keywords.json` pour ajouter ou supprimer des mots declencheurs :

```json
{
  "keywords": ["overdose", "poisoning", "allergy", "contraindication", "side effect", "..."]
}
```

Lorsqu'un mot-cle configure apparait dans la question de l'utilisateur, le systeme enregistre un evenement de risque et peut envoyer une alerte par e-mail.

### Securite du tableau de bord d'administration

Le tableau de bord d'administration restreint l'acces par liste blanche IP. Configurez dans `backend-java/src/main/resources/application.properties` :

```properties
admin.security.enabled=true
admin.security.ip-whitelist=127.0.0.1,::1
```

Ajoutez votre IP a la liste blanche si vous y accedez a distance.

### Premier lancement du modele d'embedding

Le modele d'embedding est mis en cache localement apres le premier telechargement. Si vous devez forcer un re-telechargement :

```bash
cd backend-ai
source venv/bin/activate
python -c "from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='BAAI/bge-small-zh-v1.5')"
```

## Points d'acces API

### Service IA Python (`:8001`)

| Methode | Chemin | Description |
|--------|------|-------------|
| `GET` | `/health` | Verification de l'etat |
| `POST` | `/ocr` | OCR image/PDF/Word → extraction du texte |
| `POST` | `/chat` | Reponse aux questions par RAG |
| `POST` | `/transcribe` | Parole-vers-texte (Whisper via Groq) |
| `POST` | `/analyze` | Analyse manuelle du texte |
| `GET` | `/tts` | Texte-vers-parole (edge-tts) |
| `GET` | `/search` | Recherche dans l'historique des medicaments |

### Backend Java (`:8080`)

| Methode | Chemin | Description |
|--------|------|-------------|
| `GET` | `/api/medicine/health` | Verification de l'etat |
| `POST` | `/api/medicine/recognize` | Import et reconnaissance de la notice de medicament |
| `POST` | `/api/medicine/chat` | Proxy vers le service IA pour les discussions |
| `GET` | `/api/medicine/list` | Lister tous les medicaments stockes |
| `GET` | `/api/medicine/chat-logs` | Historique des journaux de discussion (admin) |
| `GET` | `/api/medicine/analytics` | Analyses d'utilisation (admin) |
| `POST` | `/api/medicine/admin/login` | Connexion administrateur |

## Tests

```bash
# Tests unitaires Python (17 tests, ~0,2s)
cd backend-ai
source venv/bin/activate
python -m pytest tests/ -v

# Tests unitaires Java (6 tests)
cd backend-java
mvn test
```

### Couverture de tests

| Module | Tests | Couvre |
|--------|:-----:|--------|
| `check_risk_keywords` | 6 | Correspondance, cache, expiration, entree vide |
| `smart_rag_search` | 4 | Texte court, texte long, repli sur erreur, cas limites |
| `correct_medical_terms` | 7 | Filtre d'hallucination, liste noire, correction LLM, repli sur erreur |
| `MedicineController` | 6 | Tests MockMvc des endpoints REST |

## Structure du projet

```
MedVision-RAG/
├── frontend/                  # Application web monopage Vue 3 CDN
│   └── index.html             # Frontend complet (848 lignes)
├── frontend-wechat/           # Mini-programme WeChat
│   ├── pages/index/           # Page principale (WXML + JS + WXSS)
│   ├── app.js                 # Point d'entree de l'application
│   └── config.js              # Configuration des points d'acces API
├── backend-java/              # Backend metier Spring Boot
│   ├── src/main/java/com/medvision/
│   │   ├── controller/        # Endpoints REST
│   │   ├── service/           # Logique metier
│   │   ├── entity/            # Entites JPA (Medicine, ChatLog, AdminUser)
│   │   ├── repository/        # Depots Spring Data JPA
│   │   └── config/            # Securite, CORS, liste blanche IP, init des donnees
│   ├── src/test/              # Tests MockMvc
│   └── pom.xml                # Dependances Maven
├── backend-ai/                # Service IA FastAPI
│   ├── main.py                # Point d'entree des routes (~250 lignes)
│   ├── core/
│   │   ├── config.py          # Singletons globaux (LLM, embedding, client Groq)
│   │   ├── logging_config.py  # Journalisation structuree + middleware de trace
│   │   └── security.py        # Verification du jeton interne
│   ├── services/
│   │   ├── ocr.py             # OCR (ocrmac + Tesseract en secours)
│   │   ├── asr.py             # Reconnaissance vocale (Groq Whisper)
│   │   ├── rag.py             # RAG adaptatif (context stuffing + recherche vectorielle)
│   │   ├── tts.py             # Texte-vers-parole (edge-tts)
│   │   ├── risk.py            # Detection de mots-cles de risque + cache TTL
│   │   ├── email.py           # E-mail d'alerte de risque (pool de threads asynchrone)
│   │   ├── intent.py          # Analyse d'intention (medicament actuel vs historique)
│   │   ├── search.py          # Recherche dans l'historique des medicaments
│   │   └── chat_model.py      # Changement de modele de discussion
│   ├── models/
│   │   └── schemas.py         # Modeles de requete Pydantic
│   └── tests/                 # Tests unitaires pytest
├── admin_dashboard.py         # Tableau de bord d'administration Streamlit
├── risk_keywords.json         # Dictionnaire de mots-cles de risque
├── sql/
│   └── init.sql               # Script d'initialisation de la base de donnees
├── Package-Insert_Test/       # Notices de medicaments exemples pour les tests
├── .env.example               # Modele de variables d'environnement
├── .gitignore                 # Regles d'ignorance Git
├── start_all.sh               # Demarrage de tous les services en une commande
└── stop_all.sh                # Arret de tous les services en une commande
```

## FAQ

### Installation et demarrage

**`No module named 'ocrmac'`**

`ocrmac` utilise le framework macOS Vision et ne fonctionne que sur macOS. Pour Linux, installez Tesseract :

```bash
sudo apt install tesseract-ocr tesseract-ocr-chi-sim
pip install pytesseract
```

Puis modifiez `backend-ai/services/ocr.py` pour utiliser `pytesseract`.

**`Connection refused` au demarrage du backend Java**

MySQL n'est pas en cours d'execution ou le mot de passe est incorrect.

```bash
# Verifier l'etat de MySQL
mysql -u root -p -e "SELECT 1"

# Verifier que le mot de passe dans .env correspond a votre mot de passe root MySQL
cat .env | grep MYSQL_PASSWORD
```

**Avertissement `torchaudio` au demarrage de Python**

Il s'agit d'un avertissement non fatal concernant la VAD (Voice Activity Detection). Le systeme repasse en mode sans VAD et fonctionne correctement. Pour corriger : `pip install torchaudio`.

**Le telechargement Maven est lent**

Ajoutez un miroir dans `~/.m2/settings.xml` :

```xml
<mirrors>
  <mirror>
    <id>aliyun</id>
    <mirrorOf>central</mirrorOf>
    <url>https://maven.aliyun.com/repository/central</url>
  </mirror>
</mirrors>
```

### Utilisation

**Ecran blanc dans le navigateur**

Ouvrez les DevTools (F12) → onglet Console. Causes frequentes :
- Le service IA n'est pas demarre → verifiez le port `8001`
- Le backend Java n'est pas demarre → verifiez le port `8080`
- Erreur CORS → assurez-vous d'acceder via `localhost:5174`, pas `file://`

**Le mini-programme ne parvient pas a se connecter au backend**

1. Verifiez que le telephone et l'ordinateur sont sur le **même reseau Wi-Fi**
2. Verifiez que `config.js` contient votre IP locale (pas `localhost` ou `127.0.0.1`)
3. Verifiez que le pare-feu de l'ordinateur autorise les connexions entrantes sur le port `8080`
4. Essayez `curl http://VOTRE_IP_LOCALE:8080/api/medicine/health` depuis le navigateur de votre telephone

**La reconnaissance vocale ne fonctionne pas (web)**

Les navigateurs necessitent HTTPS ou `localhost` pour l'acces au microphone. Assurez-vous d'acceder a la page via `http://localhost:5174`, pas une IP locale.

**La reconnaissance vocale ne fonctionne pas (mini-programme)**

Verifiez que `GROQ_API_KEY` est defini dans `.env`. Redemarrez le service IA Python apres avoir modifie `.env`.

**L'OCR renvoie « medicament inconnu » ou du texte incoherent**

- Assurez-vous que la photo est nette et bien eclairee
- Le nom du medicament doit etre visible dans l'image
- Pour les PDF, verifiez si le fichier est une image numérisee (pas du texte recherchable) — le systeme detectera automatiquement et utilisera l'OCR d'image

### Base de donnees

**Comment reinitialiser la base de donnees**

```bash
mysql -u root -p -e "DROP DATABASE IF EXISTS medvision;"
mysql -u root -p < sql/init.sql
```

Puis redemarrez le backend Java pour recreer le compte administrateur par defaut.

**Comment changer le mot de passe administrateur**

Utilisez le tableau de bord d'administration (http://localhost:8502) apres connexion, ou mettez a jour directement dans MySQL :

```sql
USE medvision;
UPDATE admin_users SET password_hash = '$2a$10$...' WHERE username = 'admin';
```

Generez un hachage BCrypt avec n'importe quel outil en ligne ou Python :

```python
from passlib.hash import bcrypt
print(bcrypt.hash("your_new_password"))
```

## Licence

Ce depot ne contient actuellement aucun fichier de licence. Ajoutez une licence explicite avant de distribuer ou de reutiliser le projet hors du cadre prevu.
