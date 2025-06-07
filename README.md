# Feedly から Google Drive へのアーカイバー

> 🚀 **すぐに始めたい場合は**: [QUICKSTART.md](QUICKSTART.md) で5分デプロイガイドを確認してください

## プロジェクト概要

このプロジェクトは、指定された期間のFeedlyアカウントから記事を自動的に取得し、Google Driveの指定されたフォルダに個別のJSONファイルとして保存するサーバーレスソリューションを提供します。無料枠を活用してコストを最小限に抑えることに重点を置き、Google Cloud Platform（GCP）でのホスティング用に設計されています。

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
* 各記事を構造化されたJSONファイルとして特定のGoogle Driveフォルダに保存
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
    * JSONファイルが保存されるGoogle Driveフォルダ。その**フォルダID**が必要です
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
   - Feedly形式からカスタムJSON形式への変換
   - ファイル名の安全化処理
   - 日付形式の正規化

3. **Google Drive統合**
   - 環境に応じた認証方式の自動切り替え
   - 構造化されたJSONファイルのアップロード
   - エラーハンドリングとログ出力

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
- Feedlyから新しい記事を取得してGoogle Driveに保存

✅ **結果の確認**  
- Google Driveの指定フォルダにJSONファイルが作成される
- ファイル名形式：`YYYYMMDD_記事ID.json`

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

## コスト最適化

このシステムは非常にコスト効率的になるよう設計されています：

* **Cloud Functions（第2世代）：** 呼び出し、vCPU時間、メモリ時間に対して寛大な永続無料枠があります。このスクリプトの日次実行は簡単にその範囲内に収まるはずです
* **Cloud Scheduler：** 請求アカウントあたり月3つの無料ジョブを提供します。この単一ジョブは無料になります
* **Google Drive API：** この使用量レベルでは呼び出しは一般的に無料です。Google Driveストレージコストは個人/Workspaceプランに基づいて適用されます
* **Feedly API：** スクリプトは基本的なレート制限を尊重します。使用量がFeedlyの一般的なAPI制限（月間100,000リクエスト）内に留まることを確認してください

## 開発TODOリスト（GitHub Copilot用）

このリストは開発手順の概要を示します。GitHub Copilotは各タスクのコード生成を支援できます。

### フェーズ1：コアロジックとローカルテスト

* ✅ **TODO 1.1: Poetry仮想環境のセットアップと依存関係のインストール**
    * アクション：`pyproject.toml`を作成し、必要な依存関係を定義
    * アクション：`poetry install`で仮想環境を作成し、依存関係をインストール
    * 検証：依存関係が正しくインストールされる

* ✅ **TODO 1.2: 環境変数管理のセットアップ**
    * アクション：`.env`ファイルを作成し、必要な環境変数を設定
    * アクション：`python-dotenv`を使用して環境変数を読み込む関数を実装
    * アクション：`.env`ファイルを`.gitignore`に追加
    * 検証：環境変数が正しく読み込まれる

* ✅ **TODO 1.3: Feedly APIクライアント機能の実装**
    * ✅ アクション：Python関数`fetch_feedly_articles(api_token, stream_id, newer_than_timestamp_ms)`を作成
    * ✅ アクション：この関数内でFeedly API URL（`https://cloud.feedly.com/v3/streams/contents`）を構築
    * ✅ アクション：`Authorization: Bearer <api_token>`ヘッダーを設定
    * ✅ アクション：Feedly APIレスポンスからの`continuation`パラメータを使用してページネーションを処理するロジックを実装。`continuation` IDが提供されなくなるまでループ
    * ✅ アクション：APIリクエストに`count`（例：100）と`newerThan`パラメータを含める
    * ✅ アクション：各アイテムから`id`、`title`、`alternate`（`text/html`タイプのURLを取得）、`published`（タイムスタンプ）、`engagement`を抽出
    * ✅ アクション：抽出されたフィールドを持つ記事を表す辞書のリストを返す
    * ✅ アクション：HTTPリクエスト失敗に対する基本的なエラーハンドリングを追加（例：エラーを出力、空のリストを返す）
    * ✅ 検証：パブリックフィードまたはテストカテゴリからいくつかの記事を取得できる（ローカルテストには有効なトークンとストリームIDが必要）

* ✅ **TODO 1.4: JSON変換機能の実装**
    * ✅ アクション：Python関数`transform_to_json_structure(article_data)`を作成
    * ✅ アクション：入力：`fetch_feedly_articles`からの辞書
    * ✅ アクション：出力：`title`、`url`、`starCount`（`engagement`から）、`publishedDate`（Feedlyのミリ秒タイムスタンプをISO 8601文字列形式に変換、例：`datetime.utcfromtimestamp(ms/1000).isoformat() + 'Z'`）のキーを持つ新しい辞書
    * ✅ 検証：サンプル記事辞書を正しく変換する

* ✅ **TODO 1.5: Google Drive APIクライアント機能の実装（サービスアカウントキーでのローカルテスト用）**
    * ✅ アクション：Python関数`upload_to_google_drive(service_account_file_path, folder_id, file_name, json_data_string)`を作成
    * ✅ アクション：`google.oauth2.service_account.Credentials`で`googleapiclient.discovery.build`を使用してDrive APIサービスオブジェクトを作成
    * ✅ アクション：ファイルメタデータを作成：`{'name': file_name, 'parents': [folder_id]}`
    * ✅ アクション：メディアボディを作成：JSONデータ（バイトとしてエンコード）と`mimetype='application/json'`で`MediaIoBaseUpload`
    * ✅ アクション：`service.files().create(body=file_metadata, media_body=media, fields='id').execute()`を使用
    * ✅ アクション：基本的なエラーハンドリングを追加
    * ✅ 検証：ローカルに保存されたサービスアカウントJSONキーファイルを使用して、指定されたGoogle DriveフォルダにテストJSONファイルをアップロードできる（このキーファイルが`.gitignore`にあることを確認）

* ✅ **TODO 1.6: ローカルテスト用メインスクリプト**
    * ✅ アクション：`if __name__ == "__main__":`ブロックを作成
    * ✅ アクション：`python-dotenv`を使用して`.env`ファイルから環境変数を読み込み
    * ✅ アクション：固定期間（例：過去1日）に基づいて`newer_than_timestamp_ms`を計算
    * ✅ アクション：`fetch_feedly_articles`を呼び出し
    * ✅ アクション：取得した記事をループ：
        * ✅ `transform_to_json_structure`を呼び出し
        * ✅ 一意のファイル名を生成。`pathvalidate`ライブラリの`sanitize_filename`ヘルパー関数をFeedly記事IDに使用してファイル名として安全であることを確認。例：`f"{datetime.utcfromtimestamp(article['published']/1000).strftime('%Y%m%d')}_{sanitize_filename(article['id'])}.json"`
        * ✅ `upload_to_google_drive`を呼び出し
        * ✅ 進行状況を出力
    * ✅ 検証：スクリプトがローカルでエンドツーエンドで実行され、記事を取得してアップロードする

### フェーズ2: GCP Cloud Function実装

* ✅**TODO 2.1: Cloud Functionエントリーポイント用に適応（`main.py`）**
    * ✅アクション：HTTPトリガー用のCloud Functionエントリーポイント`def main(request):`を作成
    * ✅アクション：ローカルテストスクリプトからコアロジックをこの関数に移動

* ✅ **TODO 2.2: 環境変数の取得（dotenv不使用、GCP環境変数使用）**
    * ✅ アクション：`main`で、環境変数（`os.environ.get()`）から`FEEDLY_ACCESS_TOKEN`、`GOOGLE_DRIVE_FOLDER_ID`、`FEEDLY_STREAM_ID`、`FETCH_PERIOD_DAYS`、`GCP_PROJECT_ID`を読み取り
    * ✅ アクション：`FETCH_PERIOD_DAYS`に基づいて`newer_than_timestamp_ms`を計算

* ✅ **TODO 2.3: Cloud Function用にGoogle Driveアップロードを適応（ADC）**
    * ✅ アクション：Cloud Functionsで実行時にApplication Default Credentials（ADC）を使用する新しい関数`upload_to_google_drive_adc()`を作成。`google.auth.default()`が認証情報を提供
    * ✅ アクション：既存の`upload_to_google_drive()`関数は本テスト用に保持し、Cloud Function用とローカルテスト用の両方をサポート
    * ✅ アクション：Cloud Functionの`main()`関数でADC関数を使用するよう変更
    * ✅ 検証：ADCを使用してGoogle Driveにアクセスする実装が完了

* ✅ **TODO 2.4: 堅牢なログの実装**
    * ✅ アクション：標準Pythonの`logging`モジュールを使用。Cloud Functionsは`stdout`/`stderr`と`logging`出力をCloud Loggingに自動的にキャプチャ
    * ✅ アクション：以下のログを追加：関数呼び出し、取得した記事数、成功したアップロード（ファイルIDと共に）、遭遇したエラー（Feedly APIエラー、Drive APIエラー、変換エラー）
    * ✅ 検証：詳細なログが実装され、デバッグとモニタリングが可能

* ✅ **TODO 2.5: デプロイ用requirements.txt生成**
    * ✅ アクション：`poetry export -f requirements.txt --output requirements.txt --without-hashes`を使用してCloud Function用のrequirements.txtを生成
    * ✅ アクション：デプロイ前に必ずこのコマンドを実行
    * ✅ 検証：生成されたrequirements.txtが正しい依存関係を含む
    * 検証：生成されたrequirements.txtが正しい依存関係を含む

* ✅ **TODO 2.6: `main.py`と`pyproject.toml`の最終化**
    * ✅ アクション：すべてのインポートが正しいことを確認
    * ✅ アクション：`pyproject.toml`がGCP環境に必要なすべてのパッケージを含むことを確認（`pathvalidate`、`python-dotenv`含む）
    * ✅ アクション：ファイル名サニタイゼーションが最終コードで使用されることを確認
    * ✅ 検証：コードがクリーンで、よくコメントされ、潜在的な例外を適切に処理する

### フェーズ3: デプロイとスケジューリング

* ✅ **TODO 3.1: デプロイスクリプト/コマンドの作成（セットアップ手順として）**
    * ✅ アクション：必要なすべてのフラグと環境変数を含む`gcloud functions deploy`コマンドをREADMEに文書化
    * ✅ アクション：デプロイ前の`poetry export`コマンドを含める
    * ✅ アクション：自動化デプロイスクリプト`deploy.sh`を作成
    * ✅ アクション：対話形式で環境変数を安全に入力できる仕組みを実装
    * ✅ 検証：コマンドが正確で、ユーザー固有の値のプレースホルダーを含む

* ✅ **TODO 3.2: Cloud Schedulerセットアップスクリプト/コマンドの作成（セットアップ手順として）**
    * ✅ アクション：`gcloud scheduler jobs create http`コマンドをREADMEに文書化
    * ✅ アクション：自動化スケジューラースクリプト`scheduler.sh`を作成
    * ✅ アクション：スケジュール、タイムゾーン、リージョンをカスタマイズできる機能を実装
    * ✅ アクション：既存ジョブの検出と更新機能を追加
    * ✅ アクション：手動テスト実行オプションを追加
    * ✅ 検証：コマンドが正確で、関数URLの取得方法を含む

* ✅ **TODO 3.3: 管理ユーティリティとドキュメントの作成**
    * ✅ アクション：システム管理用のスクリプト`manage.sh`を作成
    * ✅ アクション：状態確認、ログ表示、手動実行、設定変更機能を実装
    * ✅ アクション：詳細デプロイメントガイド`DEPLOYMENT.md`を作成
    * ✅ アクション：クイックスタートガイド`QUICKSTART.md`を作成
    * ✅ アクション：トラブルシューティングセクションを追加
    * ✅ 検証：包括的な管理ツールとドキュメントが完成

### フェーズ4: テストと改良

* **TODO 4.1: デプロイされたCloud Functionの手動テスト**
    * アクション：デプロイ後、GCPコンソールまたは`gcloud functions call`経由でCloud Functionを手動でトリガー
    * 検証：出力とエラーについてCloud Loggingを確認。Google Driveでファイルが作成されることを確認

* **TODO 4.2: Cloud Schedulerトリガーのテスト**
    * アクション：テスト用にCloud Schedulerジョブを近い将来の時間に設定するか、スケジュールされた実行を待つ
    * 検証：関数がスケジューラによってトリガーされ、実行が成功する。ログを確認

* **TODO 4.3: コスト最適化ポイントの確認**
    * アクション：関数のメモリ設定、実行時間を二重チェック
    * アクション：不要なAPI呼び出しが行われていないことを確認
    * 検証：ソリューションが最小コストの目標に沿っている

* **TODO 4.4: 詳細なエラーハンドリングとリトライの追加**
    * アクション：429（Too Many Requests）、500、502、503、504などのHTTPステータスコードに対して指数バックオフとジッターを伴うリトライを実装。これには`tenacity`などのライブラリの使用を検討
    * 検証：FeedlyとGoogle Drive APIの両方の呼び出しで特定のHTTPエラーコードに対してリトライが試行される

## 潜在的な問題とトラブルシューティング

* **Feedly APIトークンの期限切れ：** 開発者トークンは期限切れになる可能性があります。スクリプトが動作しなくなった場合、トークンの更新が必要かどうかを確認し、`.env`ファイルまたはCloud Function環境変数で更新してください。より永続的なソリューションには、リフレッシュトークンを使用した完全なOAuth 2.0フローの実装が必要です（より複雑）
* **環境変数の設定ミス：** ローカル開発では`.env`ファイル、Cloud Functionでは環境変数として設定されていることを確認してください。設定の不一致がエラーの原因となることがあります
* **Poetry依存関係の問題：** 新しい依存関係を追加した後は、`poetry export`でrequirements.txtを再生成してからCloud Functionを再デプロイしてください
* **Feedly APIレート制限：** スクリプトは低ボリューム用に設計されていますが、広範囲な履歴取得や非常に頻繁な実行はレート制限に達する可能性があります。スクリプトは理想的にはリトライでこれを処理すべきです。デバッグが必要な場合は、Feedlyの`X-RateLimit-Count`と`X-RateLimit-Reset`ヘッダーのドキュメントを確認してください
* **Google Drive API権限：** サービスアカウントが対象フォルダに「編集者」アクセス権を持っていることを確認してください。権限エラーでアップロードが失敗する場合は、共有設定を再確認してください
* **Cloud Functionタイムアウト：** 非常に多数の記事を取得する場合、関数がタイムアウトする可能性があります（デフォルトは60秒、第2世代の最大は3600秒）。必要に応じてタイムアウト設定を調整するか、より小さなチャンクで処理するロジックを実装してください
* **Feedly APIの変更：** APIは変更される可能性があります。将来スクリプトが壊れた場合は、エンドポイントやデータ構造の更新についてFeedly開発者ドキュメントを確認してください
* **ファイル名の安全性：** Feedly項目IDには、ファイル名として安全でない文字（例：`/`、`+`）が含まれる可能性があります。この実装では`pathvalidate`ライブラリを使用してファイル名をサニタイズします。このライブラリが使用されない場合、ファイル作成が失敗する可能性があります