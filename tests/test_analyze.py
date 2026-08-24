import csv
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from config import LOTO6  # noqa: E402
import analyze  # noqa: E402


def _write_fixture_csv(path: Path, n_draws: int = 30, seed: int = 42) -> None:
    rng = random.Random(seed)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["draw_no", "draw_date", "n1", "n2", "n3", "n4", "n5", "n6", "bonus"])
        for i in range(1, n_draws + 1):
            main = sorted(rng.sample(range(1, 44), 6))
            bonus = rng.choice([n for n in range(1, 44) if n not in main])
            writer.writerow([i, f"2024/1/{i}", *main, bonus])


def test_full_report_pipeline(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_fixture_csv(data_dir / "loto6.csv")
    monkeypatch.setattr(analyze, "ROOT", tmp_path)

    draws = analyze.load_draws(LOTO6)
    assert len(draws) == 30
    assert draws[0]["main"] == sorted(draws[0]["main"])

    report = analyze.build_report(LOTO6)
    assert report["total_draws"] == 30
    assert len(report["hot_numbers_all_time"]) == 10
    assert report["sum_stats"]["min"] <= report["sum_stats"]["max"]
    assert sum(report["odd_even_distribution"].values()) == 30
    assert sum(report["high_low_distribution"].values()) == 30
    assert report["chi_square_uniformity_test"] is not None

    md = analyze.render_markdown(report, LOTO6)
    assert "ロト6" in md
    assert "カイ二乗" in md


def test_gap_since_last_seen(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    with (data_dir / "loto6.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["draw_no", "draw_date", "n1", "n2", "n3", "n4", "n5", "n6", "bonus"])
        writer.writerow([1, "2024/1/1", 1, 2, 3, 4, 5, 6, 7])
        writer.writerow([2, "2024/1/2", 1, 2, 3, 4, 5, 6, 7])
    monkeypatch.setattr(analyze, "ROOT", tmp_path)

    draws = analyze.load_draws(LOTO6)
    gaps = analyze.gap_since_last_seen(draws, LOTO6)
    assert gaps[43] == 2  # 一度も出ていない数字は最新回号と同じ経過数
    assert gaps[1] == 0  # 直近の回で出現


def test_frequency_covers_full_range(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_fixture_csv(data_dir / "loto6.csv", n_draws=5)
    monkeypatch.setattr(analyze, "ROOT", tmp_path)

    draws = analyze.load_draws(LOTO6)
    freq = analyze.frequency(draws, LOTO6, "main")
    assert set(freq.keys()) == set(range(1, 44))
    assert sum(freq.values()) == 5 * 6
