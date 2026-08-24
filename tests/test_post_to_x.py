import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from config import LOTO6  # noqa: E402
import post_to_x  # noqa: E402


def _sample_report(latest_draw_no: int = 2130) -> dict:
    return {
        "game": "ロト6",
        "total_draws": latest_draw_no,
        "latest_draw_no": latest_draw_no,
        "latest_draw_date": "2026/08/20",
        "hot_numbers_all_time": [[6, 329], [37, 320], [42, 318]],
        "cold_numbers_all_time": [[9, 258], [7, 274], [17, 275]],
        "hot_numbers_recent": [[8, 13], [18, 13], [43, 12]],
        "most_overdue_numbers": [[24, 30], [39, 23], [19, 21]],
        "bonus_frequency_top": [[6, 70], [28, 67]],
        "common_pairs": [[[5, 39], 53]],
        "sum_stats": {"mean": 132.42, "median": 132.0, "stdev": 28.48, "min": 45, "max": 212},
        "odd_even_distribution": {},
        "high_low_distribution": {},
        "consecutive_number_rate_pct": 54.3,
        "chi_square_uniformity_test": {"chi2": 30.31, "dof": 42, "p_value": 0.9103},
    }


def test_build_post_text_contains_key_facts():
    report = _sample_report()
    text = post_to_x.build_post_text(report, LOTO6)

    assert "第2130回" in text
    assert "2026/08/20" in text
    assert "6、37、42" in text  # hot top3
    assert "24、39、19" in text  # overdue top3
    assert "132.42" in text
    assert "統計的に完全ランダム" in text
    assert "#ロト6" in text


def test_state_roundtrip(tmp_path, monkeypatch):
    state_file = tmp_path / "last_posted.json"
    monkeypatch.setattr(post_to_x, "STATE_FILE", state_file)

    assert post_to_x._load_state() == {}

    post_to_x._save_state({"loto6": 2130, "loto7": 691})
    assert json.loads(state_file.read_text(encoding="utf-8")) == {"loto6": 2130, "loto7": 691}
    assert post_to_x._load_state() == {"loto6": 2130, "loto7": 691}


def test_missing_env_vars_detected(monkeypatch):
    for v in post_to_x._REQUIRED_ENV_VARS:
        monkeypatch.delenv(v, raising=False)
    assert set(post_to_x._missing_env_vars()) == set(post_to_x._REQUIRED_ENV_VARS)

    monkeypatch.setenv("X_API_KEY", "dummy")
    monkeypatch.setenv("X_API_SECRET", "dummy")
    monkeypatch.setenv("X_ACCESS_TOKEN", "dummy")
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "dummy")
    assert post_to_x._missing_env_vars() == []
