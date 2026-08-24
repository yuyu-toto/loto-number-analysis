#!/usr/bin/env python3
"""一時的な調査用スクリプト。

CSVの直接ダウンロード(/csv/loto6.csv 等)がAkamai(WAF)により403で
ブロックされることが判明したため、当せん番号案内ページ本体のHTML構造を
確認し、そこから当選番号を直接スクレイピングする方式に切り替える。
このスクリプトはその構造調査のための一時的なツールで、構造判明後に
本実装(src/fetch_data.py の書き換え)が終わったら削除してよい。
"""
from __future__ import annotations

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

TARGET_URLS = [
    # みずほ銀行本体はGitHub ActionsのIP帯がAkamai(WAF)にブロックされている
    # 可能性が高いため、コミュニティ運営のミラーサイトを調査する。
    "https://loto6.thekyo.jp/download/index",
    "https://loto7.thekyo.jp/download/index",
    "https://www.mk-mode.com/rails/loto/loto6",
    "https://www.mk-mode.com/rails/loto/loto7",
]


def _decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "cp932", "shift_jis", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def main() -> None:
    session = requests.Session()
    session.headers.update(_HEADERS)
    for url in TARGET_URLS:
        print("=" * 100)
        print(f"URL: {url}")
        try:
            resp = session.get(url, timeout=30)
            print(f"status: {resp.status_code}, content-type: {resp.headers.get('Content-Type')}")
            text = _decode(resp.content)
            print(f"length: {len(text)} chars")
            print("--- BODY (最大12000文字) ---")
            print(text[:12000])
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: {exc}")
        print()


if __name__ == "__main__":
    main()
