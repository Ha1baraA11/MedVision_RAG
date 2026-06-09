<p align="center">
  <img src="assets/logo.png" alt="MedVision-RAG Logo" width="200">
</p>

<h1 align="center">MedVision-RAG</h1>

<p align="center">
  <strong>音声対応AI医薬品アシスタント</strong><br>
  薬の添付文書を撮影するだけで、RAG＋音声で即座に回答します。
</p>

<p align="center">
  <a href="README.md">English</a> · <a href="README_CN.md">简体中文</a> · <a href="README_TW.md">繁體中文</a> · <a href="README_ko.md">한국어</a> · <a href="README_es.md">Español</a> · <a href="README_pt-BR.md">Português</a> · <a href="README_ru.md">Русский</a> · <a href="README_fr.md">Français</a> · <a href="README_de.md">Deutsch</a>
</p>

---

## 概要

MedVision-RAGは、視覚障がい者や高齢者がお薬の情報を理解できるよう支援するシステムです。薬のパッケージにカメラを向けるか、PDF・Word文書をアップロードすると、以下の処理が自動で行われます。

1. **テキスト抽出** — OCR（macOS Vision / Tesseractフォールバック）
2. **テキスト整形** — Unstructured.ioパイプラインによる空白除去、段落修復、箇条書き整理
3. **ナレッジベース構築** — テキストをベクトル化してChromaDBに格納
4. **質問応答** — アダプティブRAG（短文はコンテキストスタッキング、長文はベクトル類似検索）
5. **音声読み上げ** — edge-ttsによる回答読み上げ

システムは**Webブラウザ**、**微信ミニプログラム**、**管理ダッシュボード**（チャットログと分析の監視）に対応しています。

## 主な機能

### マルチフォーマットOCR
- **写真**：薬のパッケージ、箱、PTPシートをカメラで直接撮影
- **PDF**：テキストベースとスキャン画像の両方に対応（自動判定し画像OCRを実行）
- **Word**：テキストと表を抽出。テキストが不十分な場合は埋め込み画像のOCRにフォールバック
- **HEIC/HEIF**：iPhone写真はOCR前に自動的にJPEGへ変換

### アダプティブRAGエンジン
- **短文**（1500文字未満）：コンテキストスタッキング — 文書全体をLLMプロンプトに注入
- **長文**（1500文字以上）：ベクトル検索 — テキストをチャンクに分割しChromaDBに格納、上位K件の関連パスagesを取得
- **薬の切り替え対応**：ユーザーが別の薬の名前を言及した場合、コンテキストを自動的に切り替え

### 音声対話
- **Web**：ブラウザ標準のSpeech Recognition API（レイテンシなし、APIコストゼロ）
- **ミニプログラム**：Groq Whisper Large-V3で音声認識、edge-ttsで音声合成
- **医療用語補正**：LLMがASR出力を後処理し、誤認識された薬名を修正
- **割り込み再生対応**：読み上げボタンを押すとTTS再生を即座に停止

### リスク監視
- **キーワード検出**：`risk_keywords.json`で設定可能なリスクキーワード
- **チャットログ監査**：すべての会話をMySQLに保存しレビュー可能
- **メールアラート**：リスクキーワード検出時に自動メール通知（設定可能）
- **管理ダッシュボード**：Streamlitによるリアルタイム監視、IPホワイトリストで保護

### アクセシビリティ
- ハイコントラストUI（WCAG AA準拠）
- 大きなタッチターゲット（48px以上）
- 視覚障がい者向けの完全音声駆動ワークフロー
- 中国語・英語の言語切替対応（AI応答とTTS言語を同期）

## アーキテクチャ

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

## 動作要件

| 依存関係 | バージョン | 備考 |
|:-----------|:-------:|-------|
| Python | 3.10+ | AIサービスランタイム |
| Java | 17+ | ビジネスバックエンドランタイム |
| Maven | 3.8+ | Javaビルドツール |
| MySQL | 8.0+ | リレーショナルデータストレージ |
| macOS（推奨） | 13+ | `ocrmac`はApple Visionフレームワークを使用してOCRを実行 |

> **Linux**：動作可能ですが、OCRに[Tesseract](https://github.com/tesseract-ocr/tesseract)が必要です。`apt install tesseract-ocr tesseract-ocr-chi-sim`でインストールし、`backend-ai/services/ocr.py`を修正してください。

## APIキー

**DeepSeek APIキー**（必須）と、オプションで**Groq APIキー**（微信ミニプログラムの音声認識用）が必要です。

<details>
<summary><strong>DeepSeek APIキーの取得方法（必須）</strong></summary>

DeepSeekは質問応答用のLLMを提供しています。

1. [platform.deepseek.com](https://platform.deepseek.com/)にアクセス
2. アカウント登録またはログイン
3. 左サイドバーの**API Keys**を選択
4. **Create API Key**をクリックし、名前を入力（例：「MedVision」）
5. キーをすぐにコピー（`sk-`で始まり、再表示されません）

**コスト**：デフォルトモデル`deepseek-v4-flash`は非常に安価です。1日中の開発テストでも通常$0.01未満です。

</details>

<details>
<summary><strong>Groq APIキーの取得方法（オプション — ミニプログラム専用）</strong></summary>

GroqはLPUハードウェア上でWhisper Large-V3による高速な音声認識を提供しています。

1. [console.groq.com](https://console.groq.com/)にアクセス
2. GitHubまたはGoogleアカウントで登録
3. 左サイドバーの**API Keys**を選択
4. **Create API Key**をクリック
5. キーをコピー（`gsk-`で始まる）

**コスト**：無料プランにはWhisperの利用が十分に含まれています。Webフロントエンドはブラウザ標準の音声APIを使用するためGroqのクレジットは**消費されません**。微信ミニプログラムのみがGroqを使用します。

</details>

## インストール

### 1. クローン

```bash
git clone https://github.com/Ha1baraA11/MedVision_RAG.git
cd MedVision_RAG
```

### 2. 環境設定

```bash
cp .env.example .env
```

任意のテキストエディタで`.env`を開き、値を入力してください。

```bash
# macOS
open -e .env

# VS Code
code .env
```

| 変数名 | 必須 | 説明 |
|----------|:--------:|-------------|
| `MYSQL_PASSWORD` | **必須** | MySQLのrootパスワード |
| `DEEPSEEK_API_KEY` | **必須** | [platform.deepseek.com](https://platform.deepseek.com/)から取得 |
| `DEEPSEEK_BASE_URL` | 任意 | デフォルト：`https://api.deepseek.com` |
| `GROQ_API_KEY` | ミニプログラム用 | [console.groq.com](https://console.groq.com/)から取得 |
| `SMTP_SERVER` | 任意 | リスクアラート用SMTPサーバー（例：`smtp.qq.com`） |
| `SMTP_PORT` | 任意 | SMTPポート（QQメール：`465`） |
| `SMTP_USER` | 任意 | 送信元メールアドレス |
| `SMTP_PASSWORD` | 任意 | SMTP認証コード（メールパスワードではありません） |
| `SMTP_RECEIVER` | 任意 | 送信先メールアドレス |
| `INTERNAL_TOKEN` | 任意 | Java ↔ Python間の認証トークン |

> **注意**：`MYSQL_PASSWORD`はシステム起動に本当に必要な唯一の資格情報です。それ以外はすべて安全なデフォルト値を持つか、グレースフルデグラデーションに対応しています。

<details>
<summary><strong>QQメールのSMTP認証コード取得方法</strong></summary>

1. [mail.qq.com](https://mail.qq.com/)にログイン → 設定 → アカウント
2. **POP3/IMAP/SMTP/Exchange/CardDAV/CalDAVサービス**を見つける
3. **IMAP/SMTPサービス**を有効にする
4. SMS認証の指示に従って**認証コード**を取得
5. このコード（QQパスワードではありません）を`SMTP_PASSWORD`として使用

</details>

### 3. Python環境のセットアップ

```bash
cd backend-ai

# 仮想環境の作成
python3 -m venv venv

# 有効化
source venv/bin/activate

# 依存関係のインストール（初回のみ、約2分）
pip install -r requirements.txt
```

初回起動時にHuggingFaceから`bge-small-zh-v1.5`埋め込みモデル（約90MB）がダウンロードされます。

### 4. Java環境のセットアップ

```bash
cd backend-java

# 依存関係のダウンロードとコンパイル（初回のみ、約3分）
mvn clean install -DskipTests
```

### 5. データベースの初期化

```bash
mysql -u root -p < sql/init.sql
```

以下のリソースが作成されます：
- データベース `medvision`（UTF8MB4）
- テーブル `medicines` — 医薬品情報と全文テキスト
- テーブル `chat_logs` — 会話履歴と分析データ
- テーブル `admin_users` — 管理者アカウント

デフォルトの管理者アカウント（`admin` / `admin`）は、Javaバックエンドの初回起動時に自動作成されます。

> **代替方法**：この手順をスキップすると、Spring Bootの`hibernate.ddl-auto=update`により起動時にテーブルが自動作成されます。SQLスクリプトは明示的なスキーマ管理および本番環境デプロイ用に用意されています。

## 使い方

### クイックスタート（全サービスを一括起動）

```bash
./start_all.sh
```

このスクリプトはすべてのサービスを依存関係順に起動し、各サービスの準備完了を待ってからステータスを表示します。ログは`backend-ai/service.log`、`backend-java/backend.log`、`dashboard.log`に出力されます。

### 手動起動（3つのターミナルで個別に起動）

**ターミナル1 — Python AIサービス**（最初に起動、最も時間がかかる）

```bash
cd backend-ai
source venv/bin/activate
python main.py
```

次のメッセージを待ちます：`Uvicorn running on http://0.0.0.0:8001`

> 初回起動時に埋め込みモデル（`bge-small-zh-v1.5`）がダウンロード・キャッシュされます。2回目以降は約3秒で起動します。

**ターミナル2 — Javaバックエンド**

```bash
cd backend-java
mvn spring-boot:run
```

次のメッセージを待ちます：`Started MedVisionApplication in X.XXX seconds`

> 初回実行時にMavenが依存関係をダウンロードします。バックエンドはデータベーステーブルとデフォルトの管理者アカウントを自動作成します。

**ターミナル3 — Webフロントエンド**

```bash
cd frontend
python3 -m http.server 5174
```

ブラウザでhttp://localhost:5174を開きます。

**オプション — 管理ダッシュボード**

```bash
streamlit run admin_dashboard.py --server.port 8502
```

http://localhost:8502を開きます。ログイン：`admin` / `admin`。

### 全サービスの停止

```bash
./stop_all.sh
```

または手動で：

```bash
lsof -t -i:5174 -i:8080 -i:8001 -i:8502 | xargs kill -9
```

## 微信ミニプログラム

### セットアップ

1. [微信開発者ツール](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)をダウンロードしてインストール
2. ツールを開き、**プロジェクトのインポート**をクリック
3. `frontend-wechat/`ディレクトリを選択
4. **テストAppID**またはゲストモードを選択
5. `frontend-wechat/config.js`を編集：

```js
const API_CANDIDATES = [
  'http://192.168.x.x:8080',  // お使いのPCのLAN IPに置き換えてください
];
```

### LAN IPの確認

```bash
# macOS
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr "IPv4"
```

### 実機デバッグ

1. スマートフォンとPCが**同じWi-Fiネットワーク**に接続されていることを確認
2. 微信開発者ツールで**デバイスでデバッグ**をクリック
3. スマートフォンでQRコードをスキャン
4. 接続に失敗した場合、以下を確認：
   - PCのファイアウォールがポート`8080`の受信を許可していること
   - `config.js`に正しいLAN IPが設定されていること（`localhost`ではなく）
   - Javaバックエンドが実行中であること

## 設定

### LLMモデルの切替

`backend-ai/core/config.py`を編集：

```python
llm = ChatOpenAI(
    model="deepseek-v4-flash",   # ここでモデルを変更
    api_key=API_KEY,
    base_url=BASE_URL,
    temperature=0.3               # 0.0 = 決定論的、1.0 = 創造的
)
```

利用可能なDeepSeekモデル：
| モデル | 速度 | コスト | 推奨用途 |
|-------|:-----:|:----:|-----------------|
| `deepseek-v4-flash` | 高速 | 非常に低い | 開発・デモ（デフォルト） |
| `deepseek-v4` | 中程度 | 低 | より高品質な回答 |

### OCRエンジン

デフォルトでは`ocrmac`（macOS Vision）を使用します。LinuxでTesseractに切り替える場合：

```bash
# 中国語対応Tesseractのインストール
sudo apt install tesseract-ocr tesseract-ocr-chi-sim

# Pythonラッパーのインストール
pip install pytesseract
```

その後、`backend-ai/services/ocr.py`を修正して`ocrmac`の代わりに`pytesseract`を使用してください。

### 埋め込みモデル

デフォルトモデルは`BAAI/bge-small-zh-v1.5`（中国語医療テキスト向けに最適化、約90MB）です。ローカルのCPUで実行され、API呼び出しは不要です。変更する場合：

```python
# backend-ai/core/config.py
embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",  # ここでモデルを変更
    model_kwargs={"local_files_only": True, "device": "cpu"}
)
```

> 初回使用時は`local_files_only`を`False`に変更してHuggingFaceからダウンロードしてください。

### リスクキーワード

`risk_keywords.json`を編集してトリガーワードを追加・削除：

```json
{
  "keywords": ["過量", "中毒", "アレルギー", "禁忌", "副作用", "..."]
}
```

ユーザーの質問またはAIの応答にキーワードが含まれると、システムはイベントをログに記録し、（設定されている場合は）メールアラートを送信します。

### 管理ダッシュボードのセキュリティ

管理ダッシュボードはIPホワイトリストによるアクセス制限を行います。`backend-java/src/main/resources/application.properties`で設定：

```properties
admin.security.enabled=true
admin.security.ip-whitelist=127.0.0.1,::1
```

リモートアクセスする場合は、IPをホワイトリストに追加してください。

### 埋め込みモデルの初回セットアップ

埋め込みモデルは初回ダウンロード後にローカルにキャッシュされます。再ダウンロードが必要な場合：

```bash
cd backend-ai
source venv/bin/activate
python -c "from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='BAAI/bge-small-zh-v1.5')"
```

## APIエンドポイント

### Python AIサービス（`:8001`）

| メソッド | パス | 説明 |
|--------|------|-------------|
| `GET` | `/health` | ヘルスチェック |
| `POST` | `/ocr` | 画像・PDF・Word → テキスト抽出 |
| `POST` | `/chat` | RAG質問応答 |
| `POST` | `/transcribe` | 音声認識（Groq経由Whisper） |
| `POST` | `/analyze` | 手動テキスト分析 |
| `GET` | `/tts` | 音声合成（edge-tts） |
| `GET` | `/search` | 薬の履歴検索 |

### Javaバックエンド（`:8080`）

| メソッド | パス | 説明 |
|--------|------|-------------|
| `GET` | `/api/medicine/health` | ヘルスチェック |
| `POST` | `/api/medicine/recognize` | 添付文書のアップロードと認識 |
| `POST` | `/api/medicine/chat` | AIサービスへのチャットプロキシ |
| `GET` | `/api/medicine/list` | 保存済み薬の一覧 |
| `GET` | `/api/medicine/chat-logs` | チャットログ履歴（管理者用） |
| `GET` | `/api/medicine/analytics` | 利用分析（管理者用） |
| `POST` | `/api/medicine/admin/login` | 管理者ログイン |

## テスト

```bash
# Pythonユニットテスト（17テスト、約0.2秒）
cd backend-ai
source venv/bin/activate
python -m pytest tests/ -v

# Javaユニットテスト（6テスト）
cd backend-java
mvn test
```

### テストカバレッジ

| モジュール | テスト数 | カバレッジ |
|--------|:-----:|--------|
| `check_risk_keywords` | 6 | ヒット、キャッシュ、期限切れ、空入力 |
| `smart_rag_search` | 4 | 短文、長文、エラーフォールバック、エッジケース |
| `correct_medical_terms` | 7 | ハルシネーションフィルタ、ブラックリスト、LLM補正、エラーフォールバック |
| `MedicineController` | 6 | RESTエンドポイントMockMvcテスト |

## プロジェクト構成

```
MedVision-RAG/
├── frontend/                  # Vue 3単一ファイルWebアプリ
│   └── index.html             # フロントエンド全体（848行）
├── frontend-wechat/           # 微信ミニプログラム
│   ├── pages/index/           # メインページ（WXML + JS + WXSS）
│   ├── app.js                 # アプリエントリ
│   └── config.js              # APIエンドポイント設定
├── backend-java/              # Spring Bootビジネスバックエンド
│   ├── src/main/java/com/medvision/
│   │   ├── controller/        # RESTエンドポイント
│   │   ├── service/           # ビジネスロジック
│   │   ├── entity/            # JPAエンティティ（Medicine、ChatLog、AdminUser）
│   │   ├── repository/        # Spring Data JPAリポジトリ
│   │   └── config/            # セキュリティ、CORS、IPホワイトリスト、データ初期化
│   ├── src/test/              # MockMvcテスト
│   └── pom.xml                # Maven依存関係
├── backend-ai/                # FastAPI AIサービス
│   ├── main.py                # ルートエントリ（約250行）
│   ├── core/
│   │   ├── config.py          # グローバルシングルトン（LLM、埋め込み、Groqクライアント）
│   │   ├── logging_config.py  # 構造化ロギング＋トレースミドルウェア
│   │   └── security.py        # 内部トークン検証
│   ├── services/
│   │   ├── ocr.py             # OCR（ocrmac + Tesseractフォールバック）
│   │   ├── asr.py             # 音声認識（Groq Whisper）
│   │   ├── rag.py             # アダプティブRAG（コンテキストスタッキング＋ベクトル検索）
│   │   ├── tts.py             # 音声合成（edge-tts）
│   │   ├── risk.py            # リスクキーワード検出＋TTLキャッシュ
│   │   ├── email.py           # リスクアラートメール（非同期スレッドプール）
│   │   ├── intent.py          # 意図分析（現在 vs 過去の薬）
│   │   ├── search.py          # 薬の履歴検索
│   │   └── chat_model.py      # チャットモデル切替
│   ├── models/
│   │   └── schemas.py         # Pydanticリクエストモデル
│   └── tests/                 # pytestユニットテスト
├── admin_dashboard.py         # Streamlit管理ダッシュボード
├── risk_keywords.json         # リスクキーワード辞書
├── sql/
│   └── init.sql               # データベース初期化スクリプト
├── Package-Insert_Test/       # テスト用サンプル添付文書
├── .env.example               # 環境変数テンプレート
├── .gitignore                 # Git除外ルール
├── start_all.sh               # 全サービス一括起動スクリプト
└── stop_all.sh                # 全サービス一括停止スクリプト
```

## FAQ

### インストール・起動編

**`No module named 'ocrmac'`**

`ocrmac`はmacOS Visionフレームワークを使用するため、macOSでのみ動作します。Linuxの場合はTesseractをインストールしてください：

```bash
sudo apt install tesseract-ocr tesseract-ocr-chi-sim
pip install pytesseract
```

その後、`backend-ai/services/ocr.py`を修正して`pytesseract`を使用してください。

**Javaバックエンド起動時に`Connection refused`**

MySQLが実行されていないか、パスワードが間違っています。

```bash
# MySQLステータスの確認
mysql -u root -p -e "SELECT 1"

# .envのパスワードがMySQL rootパスワードと一致しているか確認
cat .env | grep MYSQL_PASSWORD
```

**Python起動時に`torchaudio`の警告が表示される**

VAD（音声活動検出）に関する非致命的な警告です。システムはVADなしモードにフォールバックし、正常に動作します。修正するには：`pip install torchaudio`。

**Mavenのダウンロードが遅い**

`~/.m2/settings.xml`にミラーを追加：

```xml
<mirrors>
  <mirror>
    <id>aliyun</id>
    <mirrorOf>central</mirrorOf>
    <url>https://maven.aliyun.com/repository/central</url>
  </mirror>
</mirrors>
```

### 使い方編

**ブラウザで白い画面が表示される**

DevTools（F12）→ コンソールタブを開いてください。よくある原因：
- AIサービスが起動していない → ポート`8001`を確認
- Javaバックエンドが起動していない → ポート`8080`を確認
- CORSエラー → `localhost:5174`経由でアクセスしているか確認（`file://`ではなく）

**ミニプログラムがバックエンドに接続できない**

1. スマートフォンとPCが**同じWi-Fiネットワーク**に接続されていることを確認
2. `config.js`にLAN IPが設定されていることを確認（`localhost`や`127.0.0.1`ではなく）
3. PCのファイアウォールがポート`8080`の受信接続を許可していることを確認
4. スマートフォンのブラウザから`curl http://YOUR_LAN_IP:8080/api/medicine/health`を試す

**音声認識が動作しない（Web）**

ブラウザはマイクアクセスにHTTPSまたは`localhost`を要求します。`http://localhost:5174`経由でページにアクセスしていることを確認してください（LAN IPではなく）。

**音声認識が動作しない（ミニプログラム）**

`.env`に`GROQ_API_KEY`が設定されていることを確認してください。`.env`を変更した後はPython AIサービスを再起動してください。

**OCRが「不明な薬」や文字化けを返す**

- 写真が鮮明で明るいことを確認してください
- 画像内に薬の名前が表示されている必要があります
- PDFの場合、ファイルがスキャン画像（検索可能なテキストではない）かどうか確認してください。システムが自動判定し画像OCRを使用します

### データベース編

**データベースのリセット方法**

```bash
mysql -u root -p -e "DROP DATABASE IF EXISTS medvision;"
mysql -u root -p < sql/init.sql
```

その後、Javaバックエンドを再起動してデフォルトの管理者アカウントを再作成してください。

**管理者パスワードの変更方法**

管理ダッシュボード（http://localhost:8502）にログイン後に変更するか、MySQLで直接更新：

```sql
USE medvision;
UPDATE admin_users SET password_hash = '$2a$10$...' WHERE username = 'admin';
```

BCryptハッシュはオンラインツールまたはPythonで生成：

```python
from passlib.hash import bcrypt
print(bcrypt.hash("your_new_password"))
```

## ライセンス

MIT
