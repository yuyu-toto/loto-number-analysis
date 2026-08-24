#!/usr/bin/env python3
"""みずほ銀行の当せん番号CSVを取得し、data/loto6.csv / data/loto7.csv に
正規化して書き出す。

このリポジトリの実行環境(このスクリプトを直接動かす人のPC、または
GitHub Actions)にはインターネットアクセスが必要。取得元のCSVフォーマット
(ヘッダーの有無・列順)はサイト側の変更で崩れる可能性があるため、
ヘッダー名から列を推定する方式と、既知の位置(回号,抽せん日,[曜日],本数字...,
ボーナス数字...)を仮定する方式の2通りを試す。
"""
from __future__ import annotations

import csv
import io
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import GAMES, GameConfig  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

_MAIN_RE = re.compile(r"本数字")
_BONUS_RE = re.compile(r"ボーナス")
_DRAWNO_RE = re.compile(r"回")
_DATE_RE = re.compile(r"抽[せ選]ん?日")

Draw = Tuple[int, str, List[int], List[int]]


def _decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "cp932", "shift_jis", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _fetch_csv_text(game: GameConfig) -> Tuple[str, str]:
    errors = []
    for url in game.candidate_urls:
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            if len(resp.content) < 100:
                raise ValueError("response too small, likely not a CSV")
            return _decode(resp.content), url
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{url} -> {exc}")
    raise RuntimeError(
        f"{game.name}: 候補URLすべての取得に失敗しました。"
        "サイトの構成が変わった可能性があるため src/config.py の candidate_urls を"
        "見直してください。\n" + "\n".join(errors)
    )


def _is_int(s: str) -> bool:
    try:
        int(s.strip())
        return True
    except ValueError:
        return False


def _parse_by_header(rows: List[List[str]], game: GameConfig) -> Optional[List[Draw]]:
    if not rows:
        return None
    header = rows[0]
    draw_idx = next((i for i, h in enumerate(header) if _DRAWNO_RE.search(h)), None)
    date_idx = next((i for i, h in enumerate(header) if _DATE_RE.search(h)), None)
    main_idx = [i for i, h in enumerate(header) if _MAIN_RE.search(h)]
    bonus_idx = [i for i, h in enumerate(header) if _BONUS_RE.search(h)]

    if draw_idx is None or date_idx is None:
        return None
    if len(main_idx) < game.main_count or len(bonus_idx) < game.bonus_count:
        return None

    main_idx = main_idx[: game.main_count]
    bonus_idx = bonus_idx[: game.bonus_count]
    needed_max = max([draw_idx, date_idx, *main_idx, *bonus_idx])

    parsed: List[Draw] = []
    for row in rows[1:]:
        if len(row) <= needed_max:
            continue
        try:
            draw_no = int(row[draw_idx].strip())
            main = sorted(int(row[i]) for i in main_idx)
            bonus = [int(row[i]) for i in bonus_idx]
        except ValueError:
            continue
        parsed.append((draw_no, row[date_idx].strip(), main, bonus))
    return parsed


def _parse_positional(rows: List[List[str]], game: GameConfig) -> List[Draw]:
    """回号,抽せん日,[曜日],本数字*N,ボーナス数字*B, ... を仮定した位置ベースの解析。"""
    parsed: List[Draw] = []
    for row in rows:
        if len(row) < 2 or not _is_int(row[0]):
            continue  # ヘッダー行やゴミ行をスキップ
        draw_no = int(row[0].strip())
        date = row[1].strip()
        offset = 3 if len(row) > 2 and not _is_int(row[2]) else 2
        needed = offset + game.main_count + game.bonus_count
        if len(row) < needed:
            continue
        try:
            main = sorted(int(x) for x in row[offset : offset + game.main_count])
            bonus = [
                int(x)
                for x in row[offset + game.main_count : offset + game.main_count + game.bonus_count]
            ]
        except ValueError:
            continue
        parsed.append((draw_no, date, main, bonus))
    return parsed


def _valid(draw: Draw, game: GameConfig) -> bool:
    _, _, main, bonus = draw
    if len(main) != game.main_count or len(set(main)) != game.main_count:
        return False
    if not all(game.main_min <= n <= game.main_max for n in main):
        return False
    if len(bonus) != game.bonus_count:
        return False
    if not all(game.bonus_min <= n <= game.bonus_max for n in bonus):
        return False
    return True


def fetch_and_normalize(game: GameConfig) -> List[Draw]:
    text, used_url = _fetch_csv_text(game)
    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if r]
    if not rows:
        raise RuntimeError(f"{game.name}: 取得したCSVが空でした ({used_url})")

    parsed = _parse_by_header(rows, game)
    mode = "header"
    if not parsed:
        parsed = _parse_positional(rows, game)
        mode = "positional"

    valid = [d for d in parsed if _valid(d, game)]
    if not valid:
        raise RuntimeError(
            f"{game.name}: {mode}方式でパースしましたが有効な行が0件でした ({used_url})。"
            "CSVフォーマットが想定と異なる可能性があります。"
        )

    # 回号の重複を除き、最新のもので上書きしつつ昇順に並べる
    by_draw_no = {d[0]: d for d in valid}
    ordered = sorted(by_draw_no.values(), key=lambda d: d[0])
    print(f"[{game.key}] {used_url} から {len(ordered)} 件取得 (解析方式: {mode})")
    return ordered


def write_csv(game: GameConfig, draws: List[Draw]) -> None:
    out_path = ROOT / game.data_file
    out_path.parent.mkdir(parents=True, exist_ok=True)
    main_cols = [f"n{i + 1}" for i in range(game.main_count)]
    bonus_cols = ["bonus"] if game.bonus_count == 1 else [f"bonus{i + 1}" for i in range(game.bonus_count)]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["draw_no", "draw_date", *main_cols, *bonus_cols])
        for draw_no, date, main, bonus in draws:
            writer.writerow([draw_no, date, *main, *bonus])
    print(f"[{game.key}] {out_path} に {len(draws)} 件を書き込みました")


def main() -> None:
    for game in GAMES.values():
        draws = fetch_and_normalize(game)
        write_csv(game, draws)


if __name__ == "__main__":
    main()
