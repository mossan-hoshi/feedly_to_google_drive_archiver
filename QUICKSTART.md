# 🚀 クイックスタートガイド

## 5分でデプロイ完了！

このガイドに従えば、5分以内にFeedly to Google Drive Archiverを本番稼働させることができます。

## 📋 事前準備（チェックリスト）

デプロイ前に以下を準備してください：

### ✅ Google Cloud Platform
- [ ] GCPプロジェクト作成済み
- [ ] gcloud CLIインストール・ログイン済み
- [ ] 課金有効化済み（無料枠内で運用）

### ✅ Feedly
- [ ] Feedlyアカウント作成済み
- [ ] 開発者トークン取得済み（[こちら](https://feedly.com/v3/auth/dev)）
- [ ] 対象ストリームID確認済み

### ✅ Google Drive
- [ ] アーカイブ用フォルダ作成済み
- [ ] フォルダID確認済み（URLの`folders/`以降）

## 🚀 ワンコマンドデプロイ

### ステップ1: リポジトリをクローン
```bash
git clone https://github.com/your-username/feedly_to_google_drive_archiver.git
cd feedly_to_google_drive_archiver
```

### ステップ2: 環境変数を設定

必要な設定情報を`.env`ファイルに記載し、CLI環境に読み込みます：

```bash
# .env_exampleをコピーして.envファイルを作成
cp .env_example .env

# .envファイルを編集して実際の値を設定
nano .env
```

必要な環境変数は`.env_example`ファイルを参照してください。主要な設定項目：
- `FEEDLY_ACCESS_TOKEN`: [Feedly Developer](https://feedly.com/v3/auth/dev)で取得
- `FEEDLY_STREAM_ID`: アーカイブしたいストリームID  
- `GOOGLE_DRIVE_FOLDER_ID`: アーカイブ先フォルダID（URLの`folders/`以降）
- `GCP_PROJECT_ID`: あなたのGCPプロジェクトID

環境変数をCLI環境に読み込み：
```bash
# 環境変数を読み込んでエクスポート
set -a && source .env && set +a

# 設定確認
echo "✅ 環境変数設定完了"
echo "FEEDLY_ACCESS_TOKEN: ${FEEDLY_ACCESS_TOKEN:0:20}..."
echo "FEEDLY_STREAM_ID: $FEEDLY_STREAM_ID"
echo "GOOGLE_DRIVE_FOLDER_ID: $GOOGLE_DRIVE_FOLDER_ID"
```

### ステップ3: 自動デプロイ実行
```bash
./deploy.sh YOUR_PROJECT_ID
```

スクリプトが順次以下を実行します：
1. 必要なGCP APIの有効化 ⚙️
2. requirements.txtの生成 📦
3. Cloud Functionのデプロイ ☁️
4. 環境変数の設定（対話形式） 🔧

### ステップ4: スケジューラー設定
```bash
./scheduler.sh YOUR_PROJECT_ID
```

## 🎯 実行例

```bash
# プロジェクトID: my-feedly-project の場合
./deploy.sh my-feedly-project

# 日本時間で毎日午前6時に実行する場合
./scheduler.sh my-feedly-project us-central1 "0 6 * * *" "Asia/Tokyo"
```

## ✨ デプロイ完了後の確認

### システム状態をチェック
```bash
./manage.sh status YOUR_PROJECT_ID
```

### 手動テスト実行
```bash
./manage.sh test YOUR_PROJECT_ID
```

### Google Driveで結果確認
指定したフォルダに`YYYYMMDD_記事ID.json`形式のファイルが作成されているはずです。

## 🛠️ カスタマイズ

### 実行頻度の変更
```bash
# 毎時実行
./manage.sh update-freq YOUR_PROJECT_ID us-central1 "0 * * * *"

# 週1回（日曜日）
./manage.sh update-freq YOUR_PROJECT_ID us-central1 "0 3 * * 0"
```

### 取得期間の変更
```bash
# 過去14日間の記事を取得
./manage.sh update-days YOUR_PROJECT_ID us-central1 14
```

## 🆘 トラブルシューティング

### よくある問題

**Q: 環境変数エラーが出る**
```bash
# 環境変数を確認
gcloud functions describe feedly-to-drive-archiver --region=us-central1
```

**Q: 権限エラーが出る**
- Google Driveフォルダでサービスアカウントに「編集者」権限が付与されているか確認

**Q: Feedly APIエラーが出る**
- アクセストークンが正しいか、有効期限内か確認

### ログ確認
```bash
# 詳細ログを表示
./manage.sh logs YOUR_PROJECT_ID

# エラーログのみ表示
gcloud logging read "resource.type=cloud_function AND severity>=ERROR" --limit=10
```

## 🗑️ 削除方法

システムを完全に削除する場合：
```bash
./manage.sh cleanup YOUR_PROJECT_ID
```

## 📞 サポート

- 詳細ガイド: [DEPLOYMENT.md](DEPLOYMENT.md)
- プロジェクト概要: [README.md](README.md)
- Issues: [GitHub Issues](https://github.com/your-username/feedly_to_google_drive_archiver/issues)

---

**🎉 これで完了です！システムが自動的にFeedlyの記事をGoogle Driveにアーカイブし続けます。**
