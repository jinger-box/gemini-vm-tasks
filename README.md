# gemini-vm-tasks

Gemini Web のタスク機能（専用 VM・ネットワークアクセス有効）で定期的な情報収集・監視を回すための正本リポジトリです。
VM が初期化されても `git clone` と `bootstrap.sh` の2手順で復元できる設計にしています。

## ディレクトリ構成

- `config/watch_repos.yaml`: 監視対象リポジトリとモード（`releases` / `commits`）
- `scripts/watch_github.py`: GitHub API から最新情報を取得し、前回からの差分だけを Markdown 出力するスクリプト
- `bootstrap.sh`: VM 上の作業フォルダ（`~/workspace/state`, `~/workspace/logs`, `~/.secrets`）と依存（PyYAML）を整える初期化スクリプト
- `GEMINI_PROMPTS.md`: Gemini Web にそのまま貼れる初期化・定期タスク登録用プロンプト

## ローカルでの動作確認

```bash
bash bootstrap.sh
python3 scripts/watch_github.py --state /tmp/github_watch_test.json
# 2回目（差分がなければ「新着なし」と1行出力される）
python3 scripts/watch_github.py --state /tmp/github_watch_test.json
```

## セキュリティ方針

- 公開リポジトリの監視は認証なし（60回/時）で動作します。
- レート制限を広げたい場合だけ、Public リポジトリ読み取り専用の最小権限トークンを VM 内の `~/.secrets/github.env`（`GITHUB_TOKEN=...`）に置きます。
- 認証情報・状態ファイル・ログは Git にコミットしません。
