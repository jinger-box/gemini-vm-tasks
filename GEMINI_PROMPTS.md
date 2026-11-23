# Gemini Web に貼るプロンプト集

## 1. 初回セットアップ用（専用 VM の初期化）

リポジトリを GitHub に push したあと、`<リポジトリURL>` を書き換えて Gemini Web に貼ります。

```text
専用VM（ネットワークアクセス有効）で、GitHub 更新監視タスクの環境をセットアップしてください。

手順:
1. `~/workspace` を作成し、`git clone <リポジトリURL> ~/workspace/gemini-vm-tasks` を実行する
2. `bash ~/workspace/gemini-vm-tasks/bootstrap.sh` を実行してディレクトリと必要パッケージを整える
3. `python3 ~/workspace/gemini-vm-tasks/scripts/watch_github.py` を1回実行し、初回ベースラインを `~/workspace/state/github_watch.json` に記録する
4. 実行結果とエラーの有無を日本語で簡潔に報告する

制約:
- `~/.secrets` に強い権限の鍵や個人・仕事の機密情報は置かないこと
- 状態ファイルやログは git にコミットしないこと
```

## 2. 定期タスク登録用（毎朝チェックの例）

初回セットアップが終わったら、スケジュール実行タスクとして以下を登録します。

```text
毎日朝 8:00（JST）に専用VMで以下を実行して報告してください。

手順:
1. `git -C ~/workspace/gemini-vm-tasks pull --ff-only` で最新の設定を取り込む
2. `python3 ~/workspace/gemini-vm-tasks/scripts/watch_github.py` を実行する
3. 出力が「新着なし」なら、その1行だけを簡潔に報告して終了する
4. 新着がある場合は、変更の要点を日本語で箇条書きに要約して報告する（重要なリリースがあれば変更点も短く添える）
```
