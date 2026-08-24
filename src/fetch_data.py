#!/usr/bin/env python3
"""mk-mode SITE (https://www.mk-mode.com/rails/loto/) の当選番号一覧を
ページ送りしながらスクレイピングし、data/loto6.csv / data/loto7.csv に
正規化して書き出す。

取り込むのは回号・抽選日・本数字・ボーナス数字のみ。賞金額・当選口数・
キャリーオーバーなど同サイト独自の集計列は取り込まない
(当選番号自体は公式発表された事実情報だが、それ以外の集計は同サイトの
著作物とみなせるため)。

このサイトのHTML構造が変わった場合、_parse_page() の抽出ロジックを
見直すこと。
"""
from __future__ import annotations

import csv
import re
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import GAMES, GameConfig  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REQUEST_DELAY_SEC = 0.5  # 相手サイトへの負荷軽減のためページ間に間隔を空ける

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

Draw = Tuple[int, str, List[int], List[int]]

_PAGE_COUNT_RE = re.compile(r"(\d+)\s*/\s*(\d+)")


def _new_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(_HEADERS)
    return session


def _get_soup(session: requests.Session, url: str, params: Optional[dict] = None) -> BeautifulSoup:
    resp = session.get(url, params=params, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return BeautifulSoup(resp.text, "html.parser")


def _total_pages(soup: BeautifulSoup) -> int:
    el = soup.select_one("ul.pagination li.active span")
    if not el:
        return 1
    m = _PAGE_COUNT_RE.search(el.get_text(strip=True))
    return int(m.group(2)) if m else 1


def _parse_page(soup: BeautifulSoup, game: GameConfig) -> List[Draw]:
    draws: List[Draw] = []
    for tr in soup.select("table.table-condensed tbody tr"):
        cells = tr.find_all("td")
        if len(cells) < 3:
            continue
        try:
            draw_no = int(cells[0].get_text(strip=True))
        except ValueError:
            continue
        date = cells[1].get_text(strip=True)

        raw = cells[2].get_text(separator="\n").strip()
        lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
        if len(lines) < 2:
            continue
        main_str, bonus_str = lines[0], lines[1].strip("()")
        try:
            main = sorted(int(x) for x in main_str.split())
            bonus = [int(x) for x in bonus_str.split()]
        except ValueError:
            continue

        draws.append((draw_no, date, main, bonus))
    return draws


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
    session = _new_session()
    first_soup = _get_soup(session, game.source_url, params={"page_num": 0})
    total_pages = _total_pages(first_soup)
    print(f"[{game.key}] {game.source_url} 全{total_pages}ページを取得します")

    all_draws: List[Draw] = list(_parse_page(first_soup, game))
    for page_num in range(1, total_pages):
        time.sleep(REQUEST_DELAY_SEC)
        soup = _get_soup(session, game.source_url, params={"page_num": page_num})
        all_draws.extend(_parse_page(soup, game))

    valid = [d for d in all_draws if _valid(d, game)]
    if not valid:
        raise RuntimeError(
            f"{game.name}: {game.source_url} から有効な行が1件も取得できませんでした。"
            "サイトのHTML構造が変わった可能性があります。src/fetch_data.py の"
            "_parse_page() を見直してください。"
        )

    # 回号の重複を除き、最新のもので上書きしつつ昇順に並べる
    by_draw_no = {d[0]: d for d in valid}
    ordered = sorted(by_draw_no.values(), key=lambda d: d[0])
    print(f"[{game.key}] {len(ordered)} 件取得しました (第{ordered[0][0]}回〜第{ordered[-1][0]}回)")
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
