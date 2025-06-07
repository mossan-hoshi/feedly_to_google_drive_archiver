# Feedly から Google Drive へのアーカイバー

> 🚀 **すぐに始めたい場合は**: [QUICKSTART.md](QUICKSTART.md) で5分デプロイガイドを確認してください

## プロジェクト概要

このプロジェクトは、指定された期間のFeedlyアカウントから記事を自動的に取得し、Google Driveの指定されたフォルダにCSV形式（拡張子.txt）のファイルとして保存するサーバーレスソリューションを提供します。無料枠を活用してコストを最小限に抑えることに重点を置き、Google Cloud Platform（GCP）でのホスティング用に設計されています。

主要コンポーネントには、Cloud SchedulerによってトリガーされるGoogle Cloud Function（Python）、環境変数・認証情報管理用のdotenv、Feedly APIとGoogle Drive APIとの連携が含まれます。

## 技術スタック

**開発環境：**
- Python 3.10+
- Poetry（依存関係管理）
- python-dotenv（環境変数管理）

**主要ライブラリ：**
- `requests`：Feedly API通信
- `google-api-python-client`：Google Drive API
- `google-auth`：GCP認証
- `pathvalidate`：ファイル名サニタイゼーション

**デプロイ環境：**
- Google Cloud Functions（第2世代）
- Google Cloud Scheduler
- Google Drive API

## 主な機能

* 指定されたFeedlyストリームから記事（タイトル、URL、エンゲージメントスコア、公開日）を取得
* 定義された期間（例：過去N日間）での記事フィルタリング
* 記事タイトル内のカンマや改行文字の自動クリーニング処理
* 複数記事をバッチ処理してCSV形式（拡張子.txt）で特定のGoogle Driveフォルダに保存
* Cloud Schedulerを使用した自動化と定期実行
* dotenvファイルを使用したAPIキーと設定の安全な管理
* 一般的な個人使用におけるGCP無料枠内での低コスト/無コスト運用を目指した設計

## 前提条件

開始する前に、以下があることを確認してください：

1.  **Google Cloud Platform（GCP）アカウント：**
    * 作成されたGCPプロジェクト
    * プロジェクトで有効化された課金（ただし、無料枠内に留まることが目標）
    * [Google Cloud SDK（gcloud CLI）](https://cloud.google.com/sdk/docs/install)のインストールと設定
2.  **Feedlyアカウント：**
    * Feedlyアカウント
    * **Feedly開発者アクセストークン：** このトークンを取得する必要があります
        * `https://feedly.com/v3/auth/dev`にアクセスしてみてください。ログインすると「Developer Access Token」が表示されるはずです
        * 代替方法として、Feedly Pro/Teamアカウントをお持ちの場合、`https://feedly.com/i/team/api`で新しいトークンを生成して見つけることができます
        * **重要：** このトークンは機密情報です。安全にコピーしてください
    * **Feedlyストリーム ID：** 記事を取得したいストリームのID。例：
        * すべての記事：`user/<YOUR_USER_ID>/category/global.all`（`<YOUR_USER_ID>`を実際のFeedlyユーザーIDに置き換えてください）
        * 特定のカテゴリ：`user/<YOUR_USER_ID>/category/<CATEGORY_NAME>`
        * 特定のフィード：`feed/http://myfeedurl.com/rss.xml`（フィードURLをURLエンコードしてください）
    * **FeedlyユーザーIDの確認方法：**
        * `https://feedly.com/v3/auth/dev`にアクセス
        * Feedlyアカウントでログイン
        * ページに表示される「User ID」をコピー（通常は`c805fcbf-3acf-4302-a97e-d82f9d7c897f`のような形式）
    * **Google Drive：**
    * CSVファイルが保存されるGoogle Driveフォルダ。その**フォルダID**が必要です
        * Google Driveでフォルダを開きます。URLは`https://drive.google.com/drive/folders/THIS_IS_THE_FOLDER_ID`のようになります。ID部分をコピーしてください
3.  **開発ツール（オプション、ローカルテスト用）：**
    * Python 3.8+
    * Poetry（パッケージ管理用）

## システムアーキテクチャ概要

* **Cloud Run または Cloud Function（Python 3.x）：** Feedlyからの取得、データ変換、Google Driveへのアップロードのロジックを含む
* **Cloud Scheduler：** 定義されたスケジュール（例：毎日）でCloud RunまたはCloud Functionをトリガー
* **dotenv：** FeedlyアクセストークンとGoogle DriveフォルダIDを安全に管理
* **API：** Feedly API（記事用）、Google Drive API（ファイルアップロード用）

**実装ノート：**
- スケジューリングはGCP Cloud Schedulerで実行されるため、アプリケーション内でのスケジューリング機能は不要
- Cloud RunまたはCloud Function（第2世代）での実行を想定

詳細な図については、システム仕様書を参照してください。

## 実装詳細

### 認証方式

このプロジェクトは、実行環境に応じて2つの認証方式をサポートしています：

#### Cloud Functions環境
- **Application Default Credentials (ADC)** を使用
- `google.auth.default()` で自動的に認証情報を取得
- Cloud Functions実行時にGCPが提供するサービスアカウントを使用
- サービスアカウントファイルは不要
- 関数: `upload_to_google_drive_adc()`

#### ローカルテスト環境
- **サービスアカウントJSONファイル** を使用
- `.env`ファイルで`GOOGLE_SERVICE_ACCOUNT_FILE`パスを指定
- ローカル開発とテスト用
- 関数: `upload_to_google_drive()`

### 主要機能

1. **Feedly API連携**
   - ページネーション対応（`continuation`パラメータ）
   - 指定期間によるフィルタリング
   - レート制限とエラーハンドリング

2. **データ変換**
   - Feedly形式からCSV形式への変換
   - 記事タイトルのクリーニング（カンマ、改行文字の除去）
   - ファイル名の安全化処理
   - 日付形式の正規化

3. **Google Drive統合**
   - 環境に応じた認証方式の自動切り替え
   - バッチ処理されたCSVファイル（拡張子.txt）のアップロード
   - エラーハンドリングとログ出力

### 出力形式の詳細

#### CSV構造
出力されるCSVファイルには以下の列が含まれます：

| 列名 | 説明 | 例 |
|------|------|-----|
| `title` | 記事タイトル（カンマ・改行除去済み） | "最新技術動向について" |
| `url` | 記事のURL | "https://example.com/article" |
| `starCount` | Feedlyエンゲージメントスコア | 42 |
| `publishedDate` | 公開日時（ISO8601形式） | "2025-06-07T10:30:00Z" |

#### ファイル名規則
- 形式：`feedly_articles_YYYYMMDD_HHMMSS.txt`
- 例：`feedly_articles_20250607_103000.txt`
- 拡張子：`.txt`（内容はCSV形式）

#### データクリーニング
- **タイトル処理**：カンマ（`,`）と改行文字（`\n`, `\r`）を自動除去
- **スペース正規化**：連続するスペースを単一スペースに統合
- **日付形式**：UTC基準のISO8601形式で統一

## セットアップ手順

### 🚀 クイックスタート（推奨）

最も簡単な方法でデプロイしたい場合は、提供されている自動化スクリプトを使用してください：

#### 1. リポジトリをクローン
```bash
git clone <repository-url>
cd feedly_to_google_drive_archiver
```

#### 2. 自動デプロイスクリプトを実行
```bash
./deploy.sh YOUR_PROJECT_ID [REGION]
```

#### 3. スケジューラーをセットアップ
```bash
./scheduler.sh YOUR_PROJECT_ID [REGION] [SCHEDULE] [TIMEZONE]
```

**完了！** 詳細な手順については、[DEPLOYMENT.md](DEPLOYMENT.md) を参照してください。

---

### 📋 手動セットアップ（詳細制御が必要な場合）

#### 1. 事前準備

**Google Cloud Platform (GCP) 要件:**
- GCPプロジェクトが作成済み
- Google Cloud SDK (gcloud CLI) がインストール・設定済み
- 課金が有効化済み（無料枠での運用を想定）

**Feedly 要件:**
- Feedlyアカウント
- 開発者アクセストークン（[https://feedly.com/v3/auth/dev](https://feedly.com/v3/auth/dev) で取得）
- 対象ストリームID（例：`user/YOUR_USER_ID/category/global.all`）

**Google Drive 要件:**
- アーカイブ用フォルダ作成済み
- フォルダID（URLの`folders/`以降の部分）

#### 2. GCPプロジェクトの設定

```bash
# プロジェクトを設定
gcloud config set project YOUR_PROJECT_ID

# 必要なAPIを有効化
gcloud services enable cloudfunctions.googleapis.com \
                       cloudscheduler.googleapis.com \
                       drive.googleapis.com \
                       cloudbuild.googleapis.com \
                       run.googleapis.com \
                       iam.googleapis.com \
                       artifactregistry.googleapis.com
```

#### 3. サービスアカウントの作成（オプション）

```bash
# サービスアカウントを作成
gcloud iam service-accounts create feedly-archiver-sa \
    --display-name="Feedly Archiver Service Account"

# ログ書き込み権限を付与
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:feedly-archiver-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/logging.logWriter"
```

#### 4. Google Driveフォルダを共有

1. Google Driveで対象フォルダを開く
2. 「共有」をクリック
3. サービスアカウントのメールアドレスを追加：  
   `feedly-archiver-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com`
4. 「編集者」権限を付与

#### 5. 依存関係の準備

```bash
# Poetry環境をセットアップ（初回のみ）
poetry install

# Cloud Function用requirements.txtを生成
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

#### 6. Cloud Functionのデプロイ

```bash
gcloud functions deploy feedly-to-drive-archiver \
    --gen2 \
    --runtime python311 \
    --region us-central1 \
    --source . \
    --entry-point main \
    --trigger-http \
    --allow-unauthenticated \
    --service-account feedly-archiver-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
    --timeout 540s \
    --memory 512Mi \
    --set-env-vars FEEDLY_ACCESS_TOKEN="YOUR_TOKEN",GOOGLE_DRIVE_FOLDER_ID="YOUR_FOLDER_ID",FEEDLY_STREAM_ID="YOUR_STREAM_ID",FETCH_PERIOD_DAYS="7",GCP_PROJECT_ID="YOUR_PROJECT_ID"
```

#### 7. Cloud Schedulerの設定

```bash
gcloud scheduler jobs create http feedly-archive-job \
    --location us-central1 \
    --schedule "0 3 * * *" \
    --uri "https://us-central1-YOUR_PROJECT_ID.cloudfunctions.net/feedly-to-drive-archiver" \
    --http-method GET \
    --time-zone "America/Los_Angeles" \
    --description "Triggers Feedly to Drive archiver function daily."
```

## 使用方法とモニタリング

### 自動実行

デプロイ完了後、システムは完全に自動化されます：

✅ **自動スケジュール実行**  
- Cloud Schedulerが設定されたスケジュール（デフォルト：毎日午前3時）で自動実行
- Feedlyから新しい記事を取得してCSV形式でGoogle Driveに保存

✅ **結果の確認**  
- Google Driveの指定フォルダにCSVファイル（拡張子.txt）が作成される
- ファイル名形式：`feedly_articles_YYYYMMDD_HHMMSS.txt`
- CSV形式（ヘッダー付き）：`title,url,starCount,publishedDate`

### 手動実行とテスト

#### Cloud Functionを直接テスト
```bash
# 手動で関数を実行
gcloud functions call feedly-to-drive-archiver --region=us-central1

# 実行ログを確認
gcloud functions logs read feedly-to-drive-archiver --region=us-central1 --limit=20
```

#### Schedulerジョブを手動実行
```bash
# スケジューラージョブを手動トリガー
gcloud scheduler jobs run feedly-archive-job --location=us-central1

# ジョブの状態確認
gcloud scheduler jobs describe feedly-archive-job --location=us-central1
```

### ログとモニタリング

#### Cloud Loggingでログ確認
```bash
# 最新のログを表示
gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=feedly-to-drive-archiver" --limit=50 --format="table(timestamp,severity,textPayload)"

# エラーログのみ表示
gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=feedly-to-drive-archiver AND severity>=ERROR" --limit=20
```

#### GCPコンソールでの確認
- **Cloud Functions**: [https://console.cloud.google.com/functions](https://console.cloud.google.com/functions)
- **Cloud Scheduler**: [https://console.cloud.google.com/cloudscheduler](https://console.cloud.google.com/cloudscheduler)
- **ログビューアー**: [https://console.cloud.google.com/logs](https://console.cloud.google.com/logs)

### 設定の調整

#### 実行頻度の変更
```bash
# 例：毎時実行に変更
gcloud scheduler jobs update http feedly-archive-job \
    --location=us-central1 \
    --schedule="0 * * * *"

# 例：週1回（日曜日午前3時）に変更
gcloud scheduler jobs update http feedly-archive-job \
    --location=us-central1 \
    --schedule="0 3 * * 0"
```

#### 取得期間の変更
```bash
# 例：過去14日間の記事を取得するように変更
gcloud functions deploy feedly-to-drive-archiver \
    --region=us-central1 \
    --update-env-vars FETCH_PERIOD_DAYS=14
```

### 一時停止と再開

#### 一時的に停止
```bash
# Schedulerジョブを一時停止
gcloud scheduler jobs pause feedly-archive-job --location=us-central1
```

#### 再開
```bash
# Schedulerジョブを再開
gcloud scheduler jobs resume feedly-archive-job --location=us-central1
```

### トラブルシューティング

よくある問題と解決方法については、[DEPLOYMENT.md](DEPLOYMENT.md) の「トラブルシューティング」セクションを参照してください。

#### 緊急時の対応
```bash
# すべてのジョブを一時停止
gcloud scheduler jobs pause feedly-archive-job --location=us-central1

# 関数を削除（完全停止）
gcloud functions delete feedly-to-drive-archiver --region=us-central1
```
