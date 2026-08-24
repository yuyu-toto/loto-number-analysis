#!/usr/bin/env python3
"""分析レポートから傾向まとめのポスト文を生成し、X(Twitter)に投稿する。

新しい抽選回が追加された時だけ投稿する(data/last_posted.json に前回
投稿済みの回号を記録しておき、抽選結果が増えていない回のワークフロー
実行では重複投稿しないようにしている)。

X API認証情報はGitHub Secrets経由で環境変数から読み込む:
  X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET
(取得方法・設定方法はREADMEを参照)

これらが未設定の場合はエラーにはせず、投稿をスキップしてログに
警告を出すだけにする(データ取得・分析自体は失敗させたくないため)。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import GAMES, GameConfig  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "data" / "last_posted.json"

_REQUIRED_ENV_VARS = ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET")

# Xの文字数上限(280)は「重み付き文字数」で判定され、大半の日本語文字は
# 2文字分としてカウントされる。安全マージンを取って130文字を目安にする。
_SAFE_CHAR_LIMIT = 150


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def build_post_text(report: dict, game: GameConfig) -> str:
    hot = report["hot_numbers_all_time"][:3]
    overdue = report["most_overdue_numbers"][:3]
    s = report["sum_stats"]

    hot_str = "、".join(str(n) for n, _ in hot)
    overdue_str = "、".join(str(n) for n, _ in overdue)

    lines = [
        f"【{game.name}傾向まとめ】第{report['latest_draw_no']}回({report['latest_draw_date']})時点",
        f"よく出る数字TOP3: {hot_str}",
        f"長く出ていない数字TOP3: {overdue_str}",
        f"本数字合計の平均: {s.get('mean')}",
        "※過去の頻度は次回の確率に影響しません(統計的に完全ランダム)",
        f"#{game.name} #宝くじ",
    ]
    text = "\n".join(lines)
    if len(text) > _SAFE_CHAR_LIMIT:
        print(f"[{game.key}] 警告: 投稿文が目安の{_SAFE_CHAR_LIMIT}文字を超えています({len(text)}文字)。")
    return text


def _missing_env_vars() -> list:
    return [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]


def post_tweet(text: str) -> None:
    import tweepy

    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    client.create_tweet(text=text)


def main() -> None:
    dry_run = os.environ.get("X_POST_DRY_RUN") == "1"
    missing = _missing_env_vars()
    if missing and not dry_run:
        print(
            "X API認証情報が未設定のため投稿をスキップします "
            f"(未設定の環境変数: {', '.join(missing)})。"
            "README の「Xへの自動投稿の設定」を参照してください。"
        )
        return

    state = _load_state()
    state_changed = False

    for game in GAMES.values():
        report_path = ROOT / "reports" / f"{game.key}_report.json"
        if not report_path.exists():
            print(f"[{game.key}] レポートが見つかりません。先に src/analyze.py を実行してください。")
            continue

        report = json.loads(report_path.read_text(encoding="utf-8"))
        latest_draw_no = report["latest_draw_no"]

        if state.get(game.key) == latest_draw_no:
            print(f"[{game.key}] 第{latest_draw_no}回は投稿済みのためスキップします。")
            continue

        text = build_post_text(report, game)
        print(f"[{game.key}] 投稿内容:\n{text}\n")

        if dry_run:
            print(f"[{game.key}] X_POST_DRY_RUN=1 のため実際には投稿しません。")
        else:
            post_tweet(text)
            print(f"[{game.key}] Xに投稿しました。")

        state[game.key] = latest_draw_no
        state_changed = True

    if state_changed:
        _save_state(state)


if __name__ == "__main__":
    main()
