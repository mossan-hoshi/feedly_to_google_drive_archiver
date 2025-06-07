#!/bin/bash

# Feedly to Google Drive Archiver - Cloud Function デプロイスクリプト
# 使用方法: ./deploy.sh [PROJECT_ID] [REGION] [SERVICE_ACCOUNT_EMAIL]
#
# 事前に以下の環境変数を設定することを推奨：
# export FEEDLY_ACCESS_TOKEN="your_feedly_access_token"
# export FEEDLY_STREAM_ID="your_feedly_stream_id" 
# export GOOGLE_DRIVE_FOLDER_ID="your_google_drive_folder_id"
# export FETCH_PERIOD_DAYS="7"  # オプション
#
# 環境変数が設定されていない場合は、デプロイ時に手動入力を求められます。

set -a && source .env && set +a


# デフォルト値
DEFAULT_REGION="us-central1"
DEFAULT_FUNCTION_NAME="feedly-to-drive-archiver"

# 引数の確認
if [ "$#" -lt 1 ]; then
    echo "使用方法: $0 <PROJECT_ID> [REGION] [SERVICE_ACCOUNT_EMAIL]"
    echo "例: $0 my-project-id us-central1 feedly-archiver-sa@my-project-id.iam.gserviceaccount.com"
    exit 1
fi

PROJECT_ID=$1
REGION=${2:-$DEFAULT_REGION}
SERVICE_ACCOUNT_EMAIL=$3

echo "=== Feedly to Google Drive Archiver デプロイ ==="
echo "プロジェクトID: $PROJECT_ID"
echo "リージョン: $REGION"
echo "サービスアカウント: ${SERVICE_ACCOUNT_EMAIL:-デフォルト}"
echo ""

# プロジェクトを設定
echo "1. GCPプロジェクトを設定中..."
gcloud config set project $PROJECT_ID

# 必要なAPIを有効化
echo "2. 必要なAPIを有効化中..."
gcloud services enable cloudfunctions.googleapis.com \
                       cloudscheduler.googleapis.com \
                       drive.googleapis.com \
                       cloudbuild.googleapis.com \
                       run.googleapis.com \
                       iam.googleapis.com \
                       artifactregistry.googleapis.com

# requirements.txtを最新化
echo "3. requirements.txtを生成中..."
if command -v poetry &> /dev/null; then
    poetry export -f requirements.txt --output requirements.txt --without-hashes
    echo "requirements.txtが更新されました"
else
    echo "警告: Poetryが見つかりません。既存のrequirements.txtを使用します"
fi

# 環境変数の確認
echo "4. 環境変数を確認中..."
echo ""

# 環境変数の値をチェックして表示
ENV_MISSING=false

echo "現在の環境変数の状態："
if [ -z "$FEEDLY_ACCESS_TOKEN" ]; then
    echo "❌ FEEDLY_ACCESS_TOKEN: 未設定"
    ENV_MISSING=true
else
    echo "✅ FEEDLY_ACCESS_TOKEN: ${FEEDLY_ACCESS_TOKEN:0:20}... (設定済み)"
fi

if [ -z "$FEEDLY_STREAM_ID" ]; then
    echo "❌ FEEDLY_STREAM_ID: 未設定"
    ENV_MISSING=true
else
    echo "✅ FEEDLY_STREAM_ID: $FEEDLY_STREAM_ID"
fi

if [ -z "$GOOGLE_DRIVE_FOLDER_ID" ]; then
    echo "❌ GOOGLE_DRIVE_FOLDER_ID: 未設定"
    ENV_MISSING=true
else
    echo "✅ GOOGLE_DRIVE_FOLDER_ID: $GOOGLE_DRIVE_FOLDER_ID"
fi

echo "✅ FETCH_PERIOD_DAYS: ${FETCH_PERIOD_DAYS:-7} (デフォルト値使用)"

echo ""

if [ "$ENV_MISSING" = true ]; then
    echo "⚠️  必須の環境変数が設定されていません。"
    echo ""
    echo "以下のコマンドで環境変数を設定してください："
    echo "export FEEDLY_ACCESS_TOKEN=\"your_feedly_access_token\""
    echo "export FEEDLY_STREAM_ID=\"your_feedly_stream_id\""
    echo "export GOOGLE_DRIVE_FOLDER_ID=\"your_google_drive_folder_id\""
    echo "export FETCH_PERIOD_DAYS=\"7\"  # オプション"
    echo ""
    read -p "環境変数を設定してから続行しますか？ (y/n): " -n 1 -r
else
    echo "✅ 全ての必須環境変数が設定されています。"
    read -p "これらの値でデプロイを続行しますか？ (y/n): " -n 1 -r
fi
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "環境変数を設定してから再実行してください"
    exit 1
fi

# デプロイコマンドの構築
echo "5. Cloud Functionをデプロイ中..."

DEPLOY_CMD="gcloud functions deploy $DEFAULT_FUNCTION_NAME \
    --gen2 \
    --runtime python311 \
    --region $REGION \
    --source . \
    --entry-point main \
    --trigger-http \
    --allow-unauthenticated \
    --timeout 540s \
    --memory 512Mi"

# サービスアカウントが指定されている場合は追加
if [ ! -z "$SERVICE_ACCOUNT_EMAIL" ]; then
    DEPLOY_CMD="$DEPLOY_CMD --service-account $SERVICE_ACCOUNT_EMAIL"
fi

# 環境変数の追加とデプロイ実行
echo ""
if [ "$ENV_MISSING" = true ]; then
    echo "環境変数が不足しているため、手動で入力してください："
    echo ""
    
    # 手動入力
    read -p "FEEDLY_ACCESS_TOKEN: " -s FEEDLY_TOKEN
    echo
    read -p "GOOGLE_DRIVE_FOLDER_ID: " DRIVE_FOLDER_ID
    read -p "FEEDLY_STREAM_ID: " STREAM_ID
    read -p "FETCH_PERIOD_DAYS (デフォルト: 7): " FETCH_DAYS
    FETCH_DAYS=${FETCH_DAYS:-7}
else
    echo "設定済みの環境変数を使用してデプロイします..."
    FEEDLY_TOKEN="$FEEDLY_ACCESS_TOKEN"
    DRIVE_FOLDER_ID="$GOOGLE_DRIVE_FOLDER_ID"
    STREAM_ID="$FEEDLY_STREAM_ID"
    FETCH_DAYS="${FETCH_PERIOD_DAYS:-7}"
fi

echo ""
echo "🚀 Cloud Functionをデプロイ中..."

# 実際のデプロイを実行
$DEPLOY_CMD \
    --set-env-vars FEEDLY_ACCESS_TOKEN="$FEEDLY_TOKEN",GOOGLE_DRIVE_FOLDER_ID="$DRIVE_FOLDER_ID",FEEDLY_STREAM_ID="$STREAM_ID",FETCH_PERIOD_DAYS="$FETCH_DAYS",GCP_PROJECT_ID="$PROJECT_ID"

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 デプロイが完了しました！"
    echo ""
    echo "Cloud FunctionのURL:"
    echo "https://$REGION-$PROJECT_ID.cloudfunctions.net/$DEFAULT_FUNCTION_NAME"
    echo ""
    echo "次のステップ: scheduler.shを実行してCloud Schedulerを設定してください"
else
    echo ""
    echo "❌ デプロイに失敗しました。エラーメッセージを確認してください。"
    exit 1
fi
