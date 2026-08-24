#!/usr/bin/env python3
"""data/loto6.csv, data/loto7.csv を読み込み、統計レポートを
reports/{game}_report.md と reports/{game}_report.json に出力する。

ここで計算しているのはあくまで「過去の出現傾向」の記述統計であり、
将来の当選確率を予測するものではない(抽選は独立試行のため、過去の
頻度は次回の確率に影響しない)。詳細はREADMEを参照。
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import GAMES, GameConfig  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RECENT_WINDOW = 50
TOP_N = 10


def load_draws(game: GameConfig) -> List[dict]:
    path = ROOT / game.data_file
    if not path.exists():
        raise FileNotFoundError(f"{path} が見つかりません。先に src/fetch_data.py を実行してください。")

    main_cols = [f"n{i + 1}" for i in range(game.main_count)]
    bonus_cols = ["bonus"] if game.bonus_count == 1 else [f"bonus{i + 1}" for i in range(game.bonus_count)]

    draws = []
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            main = sorted(int(row[c]) for c in main_cols)
            bonus = [int(row[c]) for c in bonus_cols]
            draws.append(
                {
                    "draw_no": int(row["draw_no"]),
                    "draw_date": row["draw_date"],
                    "main": main,
                    "bonus": bonus,
                }
            )
    draws.sort(key=lambda d: d["draw_no"])
    return draws


def frequency(draws: List[dict], game: GameConfig, key: str = "main") -> Counter:
    counter: Counter = Counter()
    for d in draws:
        counter.update(d[key])
    lo, hi = (game.main_min, game.main_max) if key == "main" else (game.bonus_min, game.bonus_max)
    for n in range(lo, hi + 1):
        counter.setdefault(n, 0)
    return counter


def gap_since_last_seen(draws: List[dict], game: GameConfig) -> Dict[int, int]:
    last_seen: Dict[int, int] = {}
    for d in draws:
        for n in d["main"]:
            last_seen[n] = d["draw_no"]
    latest_draw_no = draws[-1]["draw_no"] if draws else 0
    gaps = {}
    for n in range(game.main_min, game.main_max + 1):
        gaps[n] = latest_draw_no - last_seen[n] if n in last_seen else latest_draw_no
    return gaps


def pair_frequency(draws: List[dict], top_n: int = TOP_N):
    counter: Counter = Counter()
    for d in draws:
        for pair in combinations(d["main"], 2):
            counter[pair] += 1
    return counter.most_common(top_n)


def sum_stats(draws: List[dict]) -> dict:
    sums = [sum(d["main"]) for d in draws]
    if not sums:
        return {}
    return {
        "mean": round(statistics.mean(sums), 2),
        "median": statistics.median(sums),
        "stdev": round(statistics.pstdev(sums), 2) if len(sums) > 1 else 0,
        "min": min(sums),
        "max": max(sums),
    }


def odd_even_distribution(draws: List[dict]) -> dict:
    dist: Counter = Counter()
    for d in draws:
        odd = sum(1 for n in d["main"] if n % 2 == 1)
        dist[odd] += 1
    return dict(sorted(dist.items()))


def high_low_distribution(draws: List[dict], game: GameConfig) -> dict:
    mid = (game.main_min + game.main_max) / 2
    dist: Counter = Counter()
    for d in draws:
        high = sum(1 for n in d["main"] if n > mid)
        dist[high] += 1
    return dict(sorted(dist.items()))


def consecutive_rate(draws: List[dict]) -> float:
    if not draws:
        return 0.0
    count = 0
    for d in draws:
        nums = d["main"]
        if any(b - a == 1 for a, b in zip(nums, nums[1:])):
            count += 1
    return round(count / len(draws) * 100, 1)


def chi_square_uniformity(freq_counter: Counter, game: GameConfig) -> dict | None:
    n_values = game.main_max - game.main_min + 1
    total = sum(freq_counter.values())  # 全抽選回 × 本数字の個数(=ボール総本数)
    if n_values == 0 or total == 0:
        return None
    expected = total / n_values  # 各数字が一様に出現した場合の期待出現回数
    chi2 = sum((obs - expected) ** 2 / expected for obs in freq_counter.values())
    dof = n_values - 1
    p_value = None
    try:
        from scipy import stats as scipy_stats  # type: ignore

        p_value = float(1 - scipy_stats.chi2.cdf(chi2, dof))
    except ImportError:
        pass
    return {
        "chi2": round(chi2, 2),
        "dof": dof,
        "p_value": round(p_value, 4) if p_value is not None else None,
    }


def build_report(game: GameConfig) -> dict:
    draws = load_draws(game)
    if not draws:
        raise ValueError(f"{game.name}: データが0件です")

    recent = draws[-RECENT_WINDOW:]
    all_freq = frequency(draws, game, "main")
    recent_freq = frequency(recent, game, "main")
    bonus_freq = frequency(draws, game, "bonus")
    gaps = gap_since_last_seen(draws, game)

    return {
        "game": game.name,
        "total_draws": len(draws),
        "latest_draw_no": draws[-1]["draw_no"],
        "latest_draw_date": draws[-1]["draw_date"],
        "hot_numbers_all_time": all_freq.most_common(TOP_N),
        "cold_numbers_all_time": sorted(all_freq.items(), key=lambda kv: (kv[1], kv[0]))[:TOP_N],
        "hot_numbers_recent": recent_freq.most_common(TOP_N),
        "most_overdue_numbers": sorted(gaps.items(), key=lambda kv: -kv[1])[:TOP_N],
        "bonus_frequency_top": bonus_freq.most_common(TOP_N),
        "common_pairs": pair_frequency(draws),
        "sum_stats": sum_stats(draws),
        "odd_even_distribution": odd_even_distribution(draws),
        "high_low_distribution": high_low_distribution(draws, game),
        "consecutive_number_rate_pct": consecutive_rate(draws),
        "chi_square_uniformity_test": chi_square_uniformity(all_freq, game),
    }


def render_markdown(report: dict, game: GameConfig) -> str:
    lines = []
    lines.append(f"# {report['game']} 分析レポート")
    lines.append("")
    lines.append(
        "> ⚠️ 抽選は毎回独立した事象です。過去の出現頻度は将来の当選確率に一切影響しません"
        "(統計的に完全にランダム)。本レポートは傾向を眺めて楽しむため、および「万一当選した際に"
        "賞金を他の当選者と分け合う人数を減らす番号選び(人気の少ない組み合わせを選ぶこと)」の"
        "参考資料であり、当選を保証するものではありません。"
    )
    lines.append("")
    lines.append(
        f"- 集計対象: {report['total_draws']}回分"
        f" (最新: 第{report['latest_draw_no']}回 / {report['latest_draw_date']})"
    )
    lines.append("")

    def table(title: str, rows, cols) -> None:
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("|" + "---|" * len(cols))
        for r in rows:
            lines.append("| " + " | ".join(str(c) for c in r) + " |")
        lines.append("")

    table("出現数が多い数字 (全期間 TOP10)", report["hot_numbers_all_time"], ["数字", "出現回数"])
    table("出現数が少ない数字 (全期間 WORST10)", report["cold_numbers_all_time"], ["数字", "出現回数"])
    table(f"直近{RECENT_WINDOW}回でよく出ている数字", report["hot_numbers_recent"], ["数字", "直近出現回数"])
    table("最後に出てからの経過回数が長い数字 (未出現が続いている数字)", report["most_overdue_numbers"], ["数字", "経過回数"])
    table("ボーナス数字 出現TOP10", report["bonus_frequency_top"], ["数字", "出現回数"])
    table(
        "よく同時に出るペア TOP10",
        [(f"{a}-{b}", c) for (a, b), c in report["common_pairs"]],
        ["ペア", "出現回数"],
    )

    s = report["sum_stats"]
    lines.append("## 本数字の合計値の分布")
    lines.append("")
    lines.append(f"- 平均: {s.get('mean')}")
    lines.append(f"- 中央値: {s.get('median')}")
    lines.append(f"- 標準偏差: {s.get('stdev')}")
    lines.append(f"- 最小/最大: {s.get('min')} / {s.get('max')}")
    lines.append("")

    lines.append("## 奇数の個数の分布 (本数字のうち奇数がいくつあったか)")
    lines.append("")
    for k, v in report["odd_even_distribution"].items():
        lines.append(f"- 奇数{k}個: {v}回")
    lines.append("")

    lines.append("## 大きい数字の個数の分布 (中央値より大きい数字がいくつあったか)")
    lines.append("")
    for k, v in report["high_low_distribution"].items():
        lines.append(f"- {k}個: {v}回")
    lines.append("")

    lines.append(f"## 連続数字 (例: 12,13) を含む抽選の割合: {report['consecutive_number_rate_pct']}%")
    lines.append("")

    chi = report["chi_square_uniformity_test"]
    if chi:
        lines.append("## ランダム性の検定 (カイ二乗検定)")
        lines.append("")
        lines.append(f"- カイ二乗値: {chi['chi2']} (自由度: {chi['dof']})")
        if chi["p_value"] is not None:
            lines.append(f"- p値: {chi['p_value']}")
            verdict = (
                "有意な偏りがあるとは言えません(想定通りランダム)"
                if chi["p_value"] > 0.05
                else "統計的に有意な偏りが見られます(データ量やソースを再確認してください)"
            )
            lines.append(f"- 判定 (有意水準5%): {verdict}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    for game in GAMES.values():
        report = build_report(game)
        (out_dir / f"{game.key}_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (out_dir / f"{game.key}_report.md").write_text(render_markdown(report, game), encoding="utf-8")
        print(f"[{game.key}] レポートを reports/{game.key}_report.md に出力しました")


if __name__ == "__main__":
    main()
