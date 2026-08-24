#!/usr/bin/env python3
"""番号選びの補助ツール。

【重要】これは当選確率を上げるものではありません。ロト6・ロト7は
毎回独立した完全ランダム抽選であり、どの組み合わせも当選確率は
全く同じです。過去の出現頻度・間隔などのデータは次回の抽選結果に
一切影響しません。

ここでできることはただ一つ、「万一1等が当たったときに、賞金を
他の当選者と分け合う人数の期待値を下げること」だけです。人は
誕生日(1〜31)だけで選んだり、規則的な数列を選んだりしがちなので、
そうした人気パターンを避けたランダムな組み合わせを生成します。
"""
from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import GAMES, GameConfig  # noqa: E402


def _is_arithmetic(nums: List[int]) -> bool:
    diffs = {b - a for a, b in zip(nums, nums[1:])}
    return len(diffs) == 1


def generate_combo(game: GameConfig, avoid_birthday_range: bool = True, max_attempts: int = 1000) -> List[int]:
    nums = sorted(random.sample(range(game.main_min, game.main_max + 1), game.main_count))
    for _ in range(max_attempts):
        if avoid_birthday_range and all(n <= 31 for n in nums):
            nums = sorted(random.sample(range(game.main_min, game.main_max + 1), game.main_count))
            continue
        if _is_arithmetic(nums):
            nums = sorted(random.sample(range(game.main_min, game.main_max + 1), game.main_count))
            continue
        return nums
    return nums


def main(count_per_game: int = 5) -> None:
    print(
        "※ この組み合わせは当選確率を上げるものではありません。"
        "詳しくは src/suggest.py のdocstringとREADMEを参照してください。\n"
    )
    for game in GAMES.values():
        print(f"[{game.name}] おすすめ組み合わせ (人気パターン回避・当選確率は変わりません)")
        for i in range(count_per_game):
            combo = generate_combo(game)
            print(f"  {i + 1}: {combo}")
        print()


if __name__ == "__main__":
    main()
