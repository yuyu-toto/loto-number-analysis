"""ロト6 / ロト7 のルールとデータ取得先の設定。

みずほ銀行公式サイトはGitHub ActionsのIP帯がAkamai(WAF)にブロックされ
アクセスできなかったため、ロト愛好家コミュニティの mk-mode SITE
(https://www.mk-mode.com/rails/loto/) から当選番号一覧をスクレイピング
して取得する。取得するのは回号・抽選日・本数字・ボーナス数字のみで、
賞金額や口数など同サイト独自の集計列は取り込まない。

このサイトも将来HTML構造が変わる可能性があるため、変わった場合は
src/fetch_data.py のパース処理を見直すこと。
"""

from dataclasses import dataclass


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
    source_url: str
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
    source_url="https://www.mk-mode.com/rails/loto/loto6",
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
    source_url="https://www.mk-mode.com/rails/loto/loto7",
    data_file="data/loto7.csv",
)

GAMES = {"loto6": LOTO6, "loto7": LOTO7}
