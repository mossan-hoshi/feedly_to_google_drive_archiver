#!/bin/bash

# Feedly to Google Drive Archiver - 管理ユーティリティスクリプト
# 使用方法: ./manage.sh [COMMAND] [PROJECT_ID] [REGION]

set -e

# デフォルト値
DEFAULT_REGION="us-central1"
DEFAULT_FUNCTION_NAME="feedly-to-drive-archiver"
DEFAULT_JOB_NAME="feedly-archive-job"

# ヘルプメッセージ
show_help() {
    echo "Feedly to Google Drive Archiver - 管理ツール"
    echo ""
    echo "使用方法: $0 [COMMAND] [PROJECT_ID] [REGION]"
    echo ""
    echo "COMMANDS:"
    echo "  status       - システムの状態を確認"
    echo "  logs         - Cloud Functionのログを表示"
    echo "  test         - Cloud Functionを手動実行してテスト"
    echo "  run          - Schedulerジョブを手動実行"
    echo "  pause        - Schedulerジョブを一時停止"
    echo "  resume       - Schedulerジョブを再開"
    echo "  update-freq  - 実行頻度を変更"
    echo "  update-days  - 取得期間（日数）を変更"
    echo "  cleanup      - 全てのリソースを削除"
    echo "  help         - このヘルプを表示"
    echo ""
    echo "例:"
    echo "  $0 status my-project-id"
    echo "  $0 logs my-project-id us-central1"
    echo "  $0 test my-project-id"
    echo "  $0 update-freq my-project-id us-central1 \"0 */6 * * *\""
    echo "  $0 update-days my-project-id us-central1 14"
    echo ""
}

# 引数チェック
if [ "$#" -lt 1 ]; then
    show_help
    exit 1
fi

COMMAND=$1
PROJECT_ID=$2
REGION=${3:-$DEFAULT_REGION}

if [ "$COMMAND" = "help" ]; then
    show_help
    exit 0
fi

if [ -z "$PROJECT_ID" ] && [ "$COMMAND" != "help" ]; then
    echo "エラー: PROJECT_IDが必要です"
    show_help
    exit 1
fi

# プロジェクトを設定
gcloud config set project $PROJECT_ID

# コマンドの実行
case $COMMAND in
    "status")
        echo "=== システム状態確認 ==="
        echo "プロジェクト: $PROJECT_ID"
        echo "リージョン: $REGION"
        echo ""
        
        echo "🔧 Cloud Function状態:"
        if gcloud functions describe $DEFAULT_FUNCTION_NAME --region=$REGION &>/dev/null; then
            echo "✅ $DEFAULT_FUNCTION_NAME が稼働中"
            gcloud functions describe $DEFAULT_FUNCTION_NAME --region=$REGION --format="table(status,httpsTrigger.url)"
        else
            echo "❌ $DEFAULT_FUNCTION_NAME が見つかりません"
        fi
        
        echo ""
        echo "⏰ Cloud Scheduler状態:"
        if gcloud scheduler jobs describe $DEFAULT_JOB_NAME --location=$REGION &>/dev/null; then
            echo "✅ $DEFAULT_JOB_NAME が設定済み"
            gcloud scheduler jobs describe $DEFAULT_JOB_NAME --location=$REGION --format="table(state,schedule,timeZone)"
        else
            echo "❌ $DEFAULT_JOB_NAME が見つかりません"
        fi
        ;;
        
    "logs")
        echo "=== Cloud Functionログ表示 (最新20件) ==="
        gcloud functions logs read $DEFAULT_FUNCTION_NAME --region=$REGION --limit=20
        ;;
        
    "test")
        echo "=== Cloud Function手動実行 ==="
        echo "関数を手動で実行しています..."
        gcloud functions call $DEFAULT_FUNCTION_NAME --region=$REGION
        echo ""
        echo "実行完了。ログを確認:"
        sleep 2
        gcloud functions logs read $DEFAULT_FUNCTION_NAME --region=$REGION --limit=5
        ;;
        
    "run")
        echo "=== Schedulerジョブ手動実行 ==="
        echo "ジョブを手動実行しています..."
        gcloud scheduler jobs run $DEFAULT_JOB_NAME --location=$REGION
        echo "実行開始しました。数分後にログを確認してください。"
        ;;
        
    "pause")
        echo "=== Schedulerジョブ一時停止 ==="
        gcloud scheduler jobs pause $DEFAULT_JOB_NAME --location=$REGION
        echo "✅ ジョブが一時停止されました"
        ;;
        
    "resume")
        echo "=== Schedulerジョブ再開 ==="
        gcloud scheduler jobs resume $DEFAULT_JOB_NAME --location=$REGION
        echo "✅ ジョブが再開されました"
        ;;
        
    "update-freq")
        if [ "$#" -lt 4 ]; then
            echo "使用方法: $0 update-freq PROJECT_ID REGION \"CRON_SCHEDULE\""
            echo "例: $0 update-freq my-project us-central1 \"0 */6 * * *\""
            exit 1
        fi
        NEW_SCHEDULE=$4
        echo "=== 実行頻度更新 ==="
        echo "新しいスケジュール: $NEW_SCHEDULE"
        gcloud scheduler jobs update http $DEFAULT_JOB_NAME \
            --location=$REGION \
            --schedule="$NEW_SCHEDULE"
        echo "✅ スケジュールが更新されました"
        ;;
        
    "update-days")
        if [ "$#" -lt 4 ]; then
            echo "使用方法: $0 update-days PROJECT_ID REGION DAYS"
            echo "例: $0 update-days my-project us-central1 14"
            exit 1
        fi
        NEW_DAYS=$4
        echo "=== 取得期間更新 ==="
        echo "新しい取得期間: $NEW_DAYS 日"
        gcloud functions deploy $DEFAULT_FUNCTION_NAME \
            --region=$REGION \
            --update-env-vars FETCH_PERIOD_DAYS=$NEW_DAYS
        echo "✅ 取得期間が更新されました"
        ;;
        
    "cleanup")
        echo "=== 全リソース削除 ==="
        echo "⚠️  以下のリソースが削除されます:"
        echo "   - Cloud Function: $DEFAULT_FUNCTION_NAME"
        echo "   - Cloud Scheduler Job: $DEFAULT_JOB_NAME"
        echo ""
        read -p "本当に削除しますか？ (yes/no): " -r
        if [[ $REPLY == "yes" ]]; then
            echo "削除を実行中..."
            
            # Schedulerジョブを削除
            if gcloud scheduler jobs describe $DEFAULT_JOB_NAME --location=$REGION &>/dev/null; then
                gcloud scheduler jobs delete $DEFAULT_JOB_NAME --location=$REGION --quiet
                echo "✅ Schedulerジョブを削除しました"
            fi
            
            # Cloud Functionを削除
            if gcloud functions describe $DEFAULT_FUNCTION_NAME --region=$REGION &>/dev/null; then
                gcloud functions delete $DEFAULT_FUNCTION_NAME --region=$REGION --quiet
                echo "✅ Cloud Functionを削除しました"
            fi
            
            echo "🗑️  削除完了"
        else
            echo "削除をキャンセルしました"
        fi
        ;;
        
    *)
        echo "エラー: 不明なコマンド '$COMMAND'"
        show_help
        exit 1
        ;;
esac
