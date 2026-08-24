"""ロト6 / ロト7 のルールとデータ取得先の設定。

みずほ銀行の公式サイトはリニューアルによりURL構成が変わることがあるため、
CANDIDATE_URLS は「最初に成功したものを使う」フォールバック方式にしてある。
実行環境(GitHub Actions)で全て失敗した場合は、実際のページを確認して
ここのURLを更新すること。
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class GameConfig:
    key: str
    name: str
    main_count: int
    main_min: int
    main_max: int
    bonus_count: int
    bonus_min: int
    bonus_max: int
    candidate_urls: Tuple[str, ...]
    data_file: str


LOTO6 = GameConfig(
    key="loto6",
    name="ロト6",
    main_count=6,
    main_min=1,
    main_max=43,
    bonus_count=1,
    bonus_min=1,
    bonus_max=43,
    candidate_urls=(
        "https://www.mizuhobank.co.jp/takarakuji/check/loto/loto6/csv/loto6.csv",
        "https://www.mizuhobank.co.jp/retail/takarakuji/loto/loto6/csv/loto6.csv",
    ),
    data_file="data/loto6.csv",
)

LOTO7 = GameConfig(
    key="loto7",
    name="ロト7",
    main_count=7,
    main_min=1,
    main_max=37,
    bonus_count=2,
    bonus_min=1,
    bonus_max=37,
    candidate_urls=(
        "https://www.mizuhobank.co.jp/takarakuji/check/loto/loto7/csv/loto7.csv",
        "https://www.mizuhobank.co.jp/retail/takarakuji/loto/loto7/csv/loto7.csv",
    ),
    data_file="data/loto7.csv",
)

GAMES = {"loto6": LOTO6, "loto7": LOTO7}
