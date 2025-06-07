#!/bin/bash

# Feedly to Google Drive Archiver - Cloud Scheduler セットアップスクリプト
# 使用方法: ./scheduler.sh [PROJECT_ID] [REGION] [SCHEDULE] [TIMEZONE]

set -e

# デフォルト値
DEFAULT_REGION="us-central1"
DEFAULT_SCHEDULE="0 3 * * *"  # 毎日午前3時
DEFAULT_TIMEZONE="America/Los_Angeles"
DEFAULT_JOB_NAME="feedly-archive-job"
DEFAULT_FUNCTION_NAME="feedly-to-drive-archiver"

# 引数の確認
if [ "$#" -lt 1 ]; then
    echo "使用方法: $0 <PROJECT_ID> [REGION] [SCHEDULE] [TIMEZONE]"
    echo "例: $0 my-project-id us-central1 \"0 3 * * *\" \"Asia/Tokyo\""
    echo ""
    echo "パラメータ:"
    echo "  PROJECT_ID  : GCPプロジェクトID (必須)"
    echo "  REGION      : GCPリージョン (デフォルト: us-central1)"
    echo "  SCHEDULE    : Cronスケジュール (デフォルト: \"0 3 * * *\" - 毎日午前3時)"
    echo "  TIMEZONE    : タイムゾーン (デフォルト: America/Los_Angeles)"
    echo ""
    echo "タイムゾーンの例:"
    echo "  - Asia/Tokyo"
    echo "  - America/New_York"
    echo "  - Europe/London"
    echo "  - UTC"
    exit 1
fi

PROJECT_ID=$1
REGION=${2:-$DEFAULT_REGION}
SCHEDULE=${3:-$DEFAULT_SCHEDULE}
TIMEZONE=${4:-$DEFAULT_TIMEZONE}

echo "=== Cloud Scheduler セットアップ ==="
echo "プロジェクトID: $PROJECT_ID"
echo "リージョン: $REGION"
echo "スケジュール: $SCHEDULE"
echo "タイムゾーン: $TIMEZONE"
echo ""

# プロジェクトを設定
echo "1. GCPプロジェクトを設定中..."
gcloud config set project $PROJECT_ID

# Cloud FunctionのURLを構築
FUNCTION_URL="https://$REGION-$PROJECT_ID.cloudfunctions.net/$DEFAULT_FUNCTION_NAME"

echo "2. Cloud FunctionのURLを確認中..."
echo "URL: $FUNCTION_URL"

# Cloud Functionが存在するかチェック
echo "3. Cloud Functionの存在を確認中..."
if gcloud functions describe $DEFAULT_FUNCTION_NAME --region=$REGION &>/dev/null; then
    echo "✅ Cloud Function '$DEFAULT_FUNCTION_NAME' が見つかりました"
else
    echo "❌ Cloud Function '$DEFAULT_FUNCTION_NAME' が見つかりません"
    echo "先にdeploy.shを実行してCloud Functionをデプロイしてください"
    exit 1
fi

# 既存のスケジューラジョブを確認
echo "4. 既存のSchedulerジョブを確認中..."
if gcloud scheduler jobs describe $DEFAULT_JOB_NAME --location=$REGION &>/dev/null; then
    echo "⚠️  既存のSchedulerジョブ '$DEFAULT_JOB_NAME' が見つかりました"
    read -p "既存のジョブを削除して新しく作成しますか？ (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "既存のジョブを削除中..."
        gcloud scheduler jobs delete $DEFAULT_JOB_NAME --location=$REGION --quiet
    else
        echo "既存のジョブを更新します..."
        gcloud scheduler jobs update http $DEFAULT_JOB_NAME \
            --location=$REGION \
            --schedule="$SCHEDULE" \
            --uri="$FUNCTION_URL" \
            --http-method=GET \
            --time-zone="$TIMEZONE" \
            --description="Triggers Feedly to Drive archiver function. Schedule: $SCHEDULE, Timezone: $TIMEZONE"
        
        echo "🎉 Schedulerジョブが更新されました！"
        exit 0
    fi
fi

# 新しいSchedulerジョブを作成
echo "5. Cloud Schedulerジョブを作成中..."
gcloud scheduler jobs create http $DEFAULT_JOB_NAME \
    --location=$REGION \
    --schedule="$SCHEDULE" \
    --uri="$FUNCTION_URL" \
    --http-method=GET \
    --time-zone="$TIMEZONE" \
    --description="Triggers Feedly to Drive archiver function. Schedule: $SCHEDULE, Timezone: $TIMEZONE"

echo ""
echo "🎉 Cloud Schedulerジョブが作成されました！"
echo ""
echo "ジョブ詳細:"
echo "  名前: $DEFAULT_JOB_NAME"
echo "  スケジュール: $SCHEDULE"
echo "  タイムゾーン: $TIMEZONE"
echo "  対象URL: $FUNCTION_URL"
echo ""

# 次回実行時刻を表示
echo "次回実行時刻を確認するには:"
echo "  gcloud scheduler jobs describe $DEFAULT_JOB_NAME --location=$REGION"
echo ""

# 手動実行のオプション
read -p "今すぐテスト実行しますか？ (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "手動でジョブを実行中..."
    gcloud scheduler jobs run $DEFAULT_JOB_NAME --location=$REGION
    echo ""
    echo "✅ テスト実行を開始しました"
    echo "実行結果はCloud Loggingで確認できます:"
    echo "https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_function%22%0Aresource.labels.function_name%3D%22$DEFAULT_FUNCTION_NAME%22?project=$PROJECT_ID"
fi

echo ""
echo "セットアップ完了！"
echo ""
echo "有用なコマンド:"
echo "  # ジョブの状態確認"
echo "  gcloud scheduler jobs describe $DEFAULT_JOB_NAME --location=$REGION"
echo ""
echo "  # ジョブを一時停止"
echo "  gcloud scheduler jobs pause $DEFAULT_JOB_NAME --location=$REGION"
echo ""
echo "  # ジョブを再開"
echo "  gcloud scheduler jobs resume $DEFAULT_JOB_NAME --location=$REGION"
echo ""
echo "  # ジョブを手動実行"
echo "  gcloud scheduler jobs run $DEFAULT_JOB_NAME --location=$REGION"
