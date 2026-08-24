import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import fetch_data as fd  # noqa: E402
from config import LOTO6, LOTO7  # noqa: E402

# mk-mode SITE (https://www.mk-mode.com/rails/loto/loto6) の実際の
# HTML構造を反映した最小サンプル(2026/08/24時点で取得したものを元に作成)。
LOTO6_SAMPLE_HTML = """
<table class="table table-condensed table-striped table-hover">
  <tbody>
    <tr>
      <td class="text-right">2130</td>
      <td>2026/08/20</td>
      <td><big><strong class="text-danger">12 18 35 40 41 43<br />(03)</strong></big></td>
      <td class="text-right">1<br />510,089,600</td>
    </tr>
    <tr>
      <td class="text-right">2129</td>
      <td>2026/08/17</td>
      <td><big><strong class="text-danger">02 04 06 16 25 41<br />(40)</strong></big></td>
      <td class="text-right">0<br />0</td>
    </tr>
  </tbody>
</table>
<ul class="pagination"><li class="active"><span>1 / 107</span></li></ul>
"""

LOTO7_SAMPLE_HTML = """
<table class="table table-condensed table-striped table-hover">
  <tbody>
    <tr>
      <td class="text-right">691</td>
      <td>2026/08/21</td>
      <td><big><strong class="text-danger">08 10 20 22 23 27 37<br />(02 09)</strong></big></td>
      <td class="text-right">0<br />0</td>
    </tr>
  </tbody>
</table>
<ul class="pagination"><li class="active"><span>1 / 35</span></li></ul>
"""


def test_parse_loto6_page():
    soup = BeautifulSoup(LOTO6_SAMPLE_HTML, "html.parser")
    assert fd._total_pages(soup) == 107

    draws = fd._parse_page(soup, LOTO6)
    assert draws == [
        (2130, "2026/08/20", [12, 18, 35, 40, 41, 43], [3]),
        (2129, "2026/08/17", [2, 4, 6, 16, 25, 41], [40]),
    ]
    assert all(fd._valid(d, LOTO6) for d in draws)


def test_parse_loto7_page_two_bonus_numbers():
    soup = BeautifulSoup(LOTO7_SAMPLE_HTML, "html.parser")
    assert fd._total_pages(soup) == 35

    draws = fd._parse_page(soup, LOTO7)
    assert draws == [(691, "2026/08/21", [8, 10, 20, 22, 23, 27, 37], [2, 9])]
    assert all(fd._valid(d, LOTO7) for d in draws)


def test_total_pages_defaults_to_one_when_missing():
    soup = BeautifulSoup("<html><body>no pagination here</body></html>", "html.parser")
    assert fd._total_pages(soup) == 1


def test_invalid_row_is_rejected_by_valid():
    # 本数字が5個しかない(壊れた行)ケース
    broken = (1, "2024/1/1", [1, 2, 3, 4, 5], [6])
    assert not fd._valid(broken, LOTO6)
