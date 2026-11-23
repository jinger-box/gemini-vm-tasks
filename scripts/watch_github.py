#!/usr/bin/env python3
"""GitHub リポジトリの新着リリース・コミットを差分検知して Markdown で出力する監視スクリプト。"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from typing import Any

try:
    import yaml
except ImportError:
    print(
        "エラー: PyYAML が見つかりません。`bash bootstrap.sh` または `pip install --user pyyaml` を実行してください。",
        file=sys.stderr,
    )
    sys.exit(2)

API_BASE = "https://api.github.com"
DEFAULT_CONFIG = pathlib.Path(__file__).resolve().parent.parent / "config" / "watch_repos.yaml"
DEFAULT_STATE = pathlib.Path.home() / "workspace" / "state" / "github_watch.json"
DEFAULT_SECRETS = pathlib.Path.home() / ".secrets" / "github.env"


def load_token(secrets_path: pathlib.Path) -> str | None:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token
    if secrets_path.is_file():
        for line in secrets_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "GITHUB_TOKEN":
                return value.strip().strip('"').strip("'")
    return None


def github_get(path: str, token: str | None) -> Any:
    url = f"{API_BASE}{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "gemini-vm-tasks-watcher/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_state(path: pathlib.Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(path: pathlib.Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def check_releases(repo: str, prev_id: str | None, token: str | None, max_items: int) -> tuple[str | None, list[dict[str, str]]]:
    data = github_get(f"/repos/{repo}/releases?per_page={max_items}", token)
    if not data:
        return prev_id, []
    latest_id = str(data[0].get("tag_name") or data[0].get("id"))
    items: list[dict[str, str]] = []
    for rel in data:
        rel_id = str(rel.get("tag_name") or rel.get("id"))
        if prev_id and rel_id == prev_id:
            break
        body = (rel.get("body") or "").strip().splitlines()
        summary = " ".join(line.strip() for line in body[:3] if line.strip())[:180]
        items.append(
            {
                "id": rel_id,
                "title": rel.get("name") or rel_id,
                "date": (rel.get("published_at") or rel.get("created_at") or "")[:19].replace("T", " "),
                "url": rel.get("html_url") or "",
                "summary": summary,
            }
        )
        if prev_id is None:
            break
    return latest_id, items


def check_commits(
    repo: str,
    branch: str | None,
    prev_sha: str | None,
    token: str | None,
    max_items: int,
) -> tuple[str | None, list[dict[str, str]]]:
    query = f"per_page={max_items}"
    if branch:
        query += f"&sha={branch}"
    data = github_get(f"/repos/{repo}/commits?{query}", token)
    if not data:
        return prev_sha, []
    latest_sha = str(data[0]["sha"])
    items: list[dict[str, str]] = []
    for c in data:
        sha = str(c["sha"])
        if prev_sha and sha == prev_sha:
            break
        msg = (c.get("commit", {}).get("message") or "").splitlines()[0].strip()
        date = (c.get("commit", {}).get("committer", {}).get("date") or "")[:19].replace("T", " ")
        author = c.get("commit", {}).get("author", {}).get("name") or ""
        items.append(
            {
                "id": sha[:7],
                "title": msg,
                "date": date,
                "author": author,
                "url": c.get("html_url") or "",
            }
        )
        if prev_sha is None:
            break
    return latest_sha, items


def main() -> int:
    parser = argparse.ArgumentParser(description="GitHub 更新差分監視スクリプト")
    parser.add_argument("--config", type=pathlib.Path, default=DEFAULT_CONFIG, help="監視設定 YAML パス")
    parser.add_argument("--state", type=pathlib.Path, default=DEFAULT_STATE, help="状態保存 JSON パス")
    parser.add_argument("--secrets", type=pathlib.Path, default=DEFAULT_SECRETS, help="トークン設定ファイル")
    parser.add_argument("--max-items", type=int, default=10, help="1リポジトリあたりの最大取得件数")
    parser.add_argument("--dry-run", action="store_true", help="状態ファイルを更新せず結果だけ表示")
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    repos = cfg.get("repos") or []
    if not repos:
        print("監視対象が config に登録されていません。")
        return 0

    token = load_token(args.secrets)
    state = load_state(args.state)
    now_jst = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST")

    updates: list[str] = []
    errors: list[str] = []

    for entry in repos:
        repo = entry["repo"]
        mode = entry.get("mode", "releases")
        branch = entry.get("branch")
        note = entry.get("note", "")
        key = f"{repo}::{mode}::{branch or 'default'}"
        prev = state.get(key, {}).get("last_id")
        is_first = prev is None

        try:
            if mode == "releases":
                latest_id, items = check_releases(repo, prev, token, args.max_items)
            elif mode == "commits":
                latest_id, items = check_commits(repo, branch, prev, token, args.max_items)
            else:
                errors.append(f"- `{repo}`: 未対応の mode `{mode}`")
                continue
        except urllib.error.HTTPError as e:
            errors.append(f"- `{repo}` ({mode}): HTTP {e.code} {e.reason}")
            continue
        except Exception as e:
            errors.append(f"- `{repo}` ({mode}): {e}")
            continue

        if latest_id:
            state[key] = {"last_id": latest_id, "checked_at": now_jst}

        if items:
            header = f"### {repo}（{mode}" + (f" / {branch}" if branch else "") + ("・初回登録" if is_first else f"・新着 {len(items)} 件") + "）"
            lines = [header]
            if note:
                lines.append(f"> {note}")
            for it in items:
                line = f"- **{it['id']}** ({it['date']} UTC): {it['title']} — {it['url']}"
                lines.append(line)
                if it.get("summary"):
                    lines.append(f"  - 概要: {it['summary']}")
            updates.append("\n".join(lines))

    if not args.dry_run:
        save_state(args.state, state)

    if not updates and not errors:
        print(f"新着なし（{now_jst}・監視 {len(repos)} 件）")
        return 0

    print(f"## GitHub 監視レポート（{now_jst}）\n")
    if updates:
        print("\n\n".join(updates))
    else:
        print("新着の更新はありませんでした。")

    if errors:
        print("\n### 取得エラー\n" + "\n".join(errors))
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
