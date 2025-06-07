# 🚀 クイックデプロイメントガイド

このガイドでは、Feedly to Google Drive ArchiverをGoogle Cloud Functionとしてデプロイする手順を説明します。

## 前提条件の確認

1. **Google Cloud Platform (GCP) アカウント**
   - GCPプロジェクトが作成済み
   - Google Cloud SDK (gcloud CLI) がインストール・設定済み
   - 課金が有効化済み（無料枠内での運用を想定）

2. **Feedly アカウント**
   - Feedly開発者アクセストークン取得済み
   - 対象ストリームIDの確認済み

3. **Google Drive**
   - アーカイブ用フォルダ作成済み
   - フォルダIDの確認済み

## ワンステップデプロイメント

### ステップ1: リポジトリをクローンして移動
```bash
git clone <repository-url>
cd feedly_to_google_drive_archiver
```

### ステップ2: 環境変数を設定

`.env`ファイルに必要な設定を記載し、CLI環境に読み込みます：

#### 2-1. .envファイルを作成・編集
```bash
# .env_exampleをコピーして.envファイルを作成
cp .env_example .env

# .envファイルを編集して実際の値を設定
nano .env
```

必要な環境変数は`.env_example`ファイルを参照してください。各値を実際の値に置き換えます：
- `FEEDLY_ACCESS_TOKEN`: [Feedly Developer](https://feedly.com/v3/auth/dev)で取得
- `FEEDLY_STREAM_ID`: アーカイブしたいストリームID
- `GOOGLE_DRIVE_FOLDER_ID`: アーカイブ先フォルダID
- `GCP_PROJECT_ID`: あなたのGCPプロジェクトID

#### 2-2. 環境変数をCLI環境に読み込み
```bash
# .envファイルから環境変数を読み込み
set -a && source .env && set +a

# 設定確認
echo "FEEDLY_ACCESS_TOKEN: ${FEEDLY_ACCESS_TOKEN:0:20}..."
echo "FEEDLY_STREAM_ID: $FEEDLY_STREAM_ID"
echo "GOOGLE_DRIVE_FOLDER_ID: $GOOGLE_DRIVE_FOLDER_ID"
echo "FETCH_PERIOD_DAYS: $FETCH_PERIOD_DAYS"
```

### ステップ3: デプロイスクリプトを実行
```bash
./deploy.sh YOUR_PROJECT_ID [REGION] [SERVICE_ACCOUNT_EMAIL]
```

例:
```bash
# 基本的なデプロイ
./deploy.sh my-project-id

# リージョンを指定
./deploy.sh my-project-id us-central1

# サービスアカウントも指定
./deploy.sh my-project-id us-central1 feedly-archiver-sa@my-project-id.iam.gserviceaccount.com
```

スクリプトが以下を自動実行します：
- 必要なGCP APIの有効化
- requirements.txtの生成
- Cloud Functionのデプロイ
- 環境変数の設定

### ステップ4: スケジューラーをセットアップ
```bash
./scheduler.sh YOUR_PROJECT_ID [REGION] [SCHEDULE] [TIMEZONE]
```

例:
```bash
# 毎日午前3時（太平洋時間）に実行
./scheduler.sh my-project-id

# 毎日午前6時（日本時間）に実行
./scheduler.sh my-project-id us-central1 "0 6 * * *" "Asia/Tokyo"

# 毎時実行
./scheduler.sh my-project-id us-central1 "0 * * * *" "UTC"
```

## 手動デプロイメント

自動スクリプトを使用しない場合の手動手順：

### 1. 必要なAPIを有効化
```bash
gcloud config set project YOUR_PROJECT_ID

gcloud services enable cloudfunctions.googleapis.com \
                       cloudscheduler.googleapis.com \
                       drive.googleapis.com \
                       cloudbuild.googleapis.com \
                       run.googleapis.com \
                       iam.googleapis.com \
                       artifactregistry.googleapis.com
```

### 2. サービスアカウントを作成（オプション）
```bash
gcloud iam service-accounts create feedly-archiver-sa \
    --display-name="Feedly Archiver Service Account"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:feedly-archiver-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/logging.logWriter"
```

### 3. 環境変数を設定

デプロイ前に環境変数を準備します：

#### 3-1. .envファイルを作成
```bash
# .env_exampleをコピーして.envファイルを作成
cp .env_example .env

# .envファイルを編集して実際の値を設定
nano .env
```

必要な環境変数は`.env_example`ファイルを参照してください。各値を実際の値に置き換えます。

#### 3-2. 環境変数をCLI環境に読み込み
```bash
# 環境変数を読み込み
set -a && source .env && set +a

# 設定確認
echo "環境変数設定完了: FEEDLY_ACCESS_TOKEN=${FEEDLY_ACCESS_TOKEN:0:20}..."
```

4. **Google DriveフォルダをサービスアカウントEA共有
- Google Driveで対象フォルダを開く
- 「共有」をクリック
- `feedly-archiver-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com` を追加
- 「編集者」権限を付与

### 5. requirements.txtを生成
```bash
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

### 6. Cloud Functionをデプロイ
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
    --set-env-vars FEEDLY_ACCESS_TOKEN="YOUR_FEEDLY_ACCESS_TOKEN",GOOGLE_DRIVE_FOLDER_ID="YOUR_GOOGLE_DRIVE_FOLDER_ID",FEEDLY_STREAM_ID="YOUR_FEEDLY_STREAM_ID",FETCH_PERIOD_DAYS="7",GCP_PROJECT_ID="YOUR_PROJECT_ID"
```

### 7. Cloud Schedulerジョブを作成
```bash
gcloud scheduler jobs create http feedly-archive-job \
    --location us-central1 \
    --schedule "0 3 * * *" \
    --uri "https://us-central1-YOUR_PROJECT_ID.cloudfunctions.net/feedly-to-drive-archiver" \
    --http-method GET \
    --time-zone "America/Los_Angeles" \
    --description "Triggers Feedly to Drive archiver function daily."
```

## デプロイ後の確認

### Cloud Functionの動作確認
```bash
# 手動でテスト実行
gcloud functions call feedly-to-drive-archiver --region=us-central1

# ログを確認
gcloud functions logs read feedly-to-drive-archiver --region=us-central1
```

### Cloud Schedulerの確認
```bash
# ジョブの状態確認
gcloud scheduler jobs describe feedly-archive-job --location=us-central1

# 手動実行
gcloud scheduler jobs run feedly-archive-job --location=us-central1
```

### Google Driveでファイル確認
- 指定したGoogle Driveフォルダに
- JSON形式のファイルが作成されていることを確認

## トラブルシューティング

### よくある問題と解決方法

1. **権限エラー**
   - サービスアカウントがGoogle Driveフォルダに「編集者」権限を持っているか確認
   - GCP IAMでサービスアカウントに必要な権限があるか確認

2. **環境変数エラー**
   - Cloud Functionの環境変数が正しく設定されているか確認
   - 環境変数の値に特殊文字が含まれていないか確認

3. **Feedly APIエラー**
   - アクセストークンが有効か確認
   - ストリームIDが正しいか確認
   - レート制限に達していないか確認

4. **デプロイエラー**
   - requirements.txtが最新か確認
   - Pythonランタイムバージョンが正しいか確認

### ログの確認方法
```bash
# Cloud Functionのログ
gcloud functions logs read feedly-to-drive-archiver --region=us-central1 --limit=50

# Cloud Schedulerのログ
gcloud logging read "resource.type=gce_instance AND jsonPayload.job_name=feedly-archive-job" --limit=10
```

## 管理コマンド

### スケジューラーの管理
```bash
# ジョブを一時停止
gcloud scheduler jobs pause feedly-archive-job --location=us-central1

# ジョブを再開
gcloud scheduler jobs resume feedly-archive-job --location=us-central1

# ジョブを削除
gcloud scheduler jobs delete feedly-archive-job --location=us-central1
```

### Cloud Functionの管理
```bash
# 関数を削除
gcloud functions delete feedly-to-drive-archiver --region=us-central1

# 環境変数を更新
gcloud functions deploy feedly-to-drive-archiver \
    --region=us-central1 \
    --update-env-vars FETCH_PERIOD_DAYS=14
```

## コスト最適化のヒント

- **実行頻度の調整**: 必要以上に頻繁な実行を避ける
- **メモリ設定の最適化**: 512MiB以下で十分動作するように設計済み
- **タイムアウト設定**: 通常30秒以内で完了するため、不要に長いタイムアウトを避ける
- **無料枠の活用**: Cloud Functions、Cloud Scheduler共に寛大な無料枠内で運用可能
