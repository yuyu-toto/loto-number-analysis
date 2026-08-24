# loto-number-analysis

ロト6・ロト7の過去の当選番号を自動取得し、出現頻度・出現間隔・偶奇バランス・
合計値の分布などを分析してレポート化するツールです。

## 最初に知っておいてほしいこと

ロト6・ロト7は毎回独立したくじ引き(乱数抽選)です。統計学的に、
**過去にどの数字が何回出たかは、次回どの数字が出るかに一切影響しません。**
「最近出ていない数字はそろそろ出る」「よく出る数字はまた出やすい」は
どちらも誤りです(いわゆるギャンブラーの誤謬)。本ツールが出す
カイ二乗検定の結果も、基本的には「偏りなし(p値 > 0.05)」になります
(それが正しい状態です)。

このツールで現実的に意味があるのは次の2つだけです。

1. **傾向を眺めて楽しむこと。** データを見ること自体が目的。
2. **当せん時に賞金を分け合う人数の期待値を下げること。** 多くの人は
   誕生日(1〜31)だけで選んだり、規則的な数列を選んだりする傾向があるため、
   そうした「人気パターン」を避けると、万一1等が当たった場合に
   同じ番号を選んでいた他の当選者と山分けになる確率をわずかに下げられます
   (`src/suggest.py` はこの目的のためだけのツールで、当選確率自体は
   1ミリも変えません)。

このツールは当選を保証するものではありません。あくまで分析・記録用です。

## 機能

- `src/fetch_data.py`: 当せん番号一覧を取得し、
  `data/loto6.csv` / `data/loto7.csv` に正規化して保存
- `src/analyze.py`: 保存済みデータから統計レポートを生成
  (`reports/loto6_report.md` / `reports/loto7_report.md` と `.json`)
  - 出現頻度(全期間 / 直近50回)の多い数字・少ない数字
  - 最後に出てからの経過回数(未出現が続いている数字)
  - よく同時に出る数字のペア
  - ボーナス数字の出現頻度
  - 本数字の合計値の統計(平均・中央値・標準偏差)
  - 奇数/偶数の個数分布、大きい数字/小さい数字の個数分布
  - 連続数字を含む抽選の割合
  - カイ二乗検定によるランダム性の確認
- `src/suggest.py`: 人気パターン(誕生日範囲のみ・規則的な数列)を避けた
  ランダムな組み合わせを提案(当選確率は変わりません。上記参照)
- `src/post_to_x.py`: レポートから傾向まとめの投稿文を生成し、X(旧Twitter)
  に自動投稿する。新しい抽選回が追加された時だけ投稿し、重複投稿はしない
- `.github/workflows/update.yml`: 抽選日の夜に自動でデータ取得・分析・
  X投稿・コミットするスケジュール実行

## セットアップ (ローカルで実行する場合)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python src/fetch_data.py   # data/loto6.csv, data/loto7.csv を取得
python src/analyze.py      # reports/ にレポートを生成
python src/suggest.py      # 番号提案(任意)

# Xへの投稿内容だけ確認したい場合(実際には投稿しない)
X_POST_DRY_RUN=1 python src/post_to_x.py
```

## GitHub Actionsでの自動運用

`.github/workflows/update.yml` が、ロト6の抽選日(月・木)とロト7の
抽選日(金)の夜に自動実行され、最新データの取得・分析・コミットまで
行います。手動実行したい場合はGitHubの「Actions」タブから
`Update Loto Data & Report` を `workflow_dispatch` で起動してください。

## データ取得元について (重要な注意)

当初はみずほ銀行公式サイトのCSVを直接取得する方式だったが、
**GitHub ActionsのIPアドレス帯がみずほ銀行のWAF(Akamai)に一律で
ブロックされており**(すべてのページで `Access Denied` / Akamaiの
エラーページが返る)、取得できないことが判明した。

そのため、ロト愛好家コミュニティが運営する
[mk-mode SITE](https://www.mk-mode.com/rails/loto/loto6) の当選番号一覧
ページをスクレイピングする方式に切り替えている(`src/config.py` の
`source_url`)。取得するのは **回号・抽選日・本数字・ボーナス数字のみ**。
賞金額・当選口数・キャリーオーバーなど同サイト独自の集計列は、当選番号
そのもの(公式発表された事実情報)とは異なり同サイトの著作物とみなせる
ため取り込んでいない。

- 全ページを取得するため、`REQUEST_DELAY_SEC`(既定0.5秒)ずつ間隔を
  空けてページ送りしている。全履歴取得には数分かかる場合がある。
- **もしこのサイトのHTML構造が変わった場合**、GitHub Actionsのログに
  「有効な行が1件も取得できませんでした」というエラーが出る。その場合は
  実際のページ( https://www.mk-mode.com/rails/loto/loto6 など )を確認し、
  `src/fetch_data.py` の `_parse_page()` / `_total_pages()` を実際の
  HTML構造に合わせて修正すること。
- 別のデータ源に切り替えたい場合は `src/config.py` の `source_url` と
  `src/fetch_data.py` のパース処理を差し替えればよい。

## Xへの自動投稿の設定

新しい抽選結果が出るたびに、傾向まとめ(よく出る数字TOP3・長く出ていない
数字TOP3・本数字合計の平均など)を自動でXに投稿できます。投稿文の例:

```
【ロト6傾向まとめ】第2130回(2026/08/20)時点
よく出る数字TOP3: 6、37、42
長く出ていない数字TOP3: 24、39、19
本数字合計の平均: 132.42
※過去の頻度は次回の確率に影響しません(統計的に完全ランダム)
#ロト6 #宝くじ
```

### 1. X Developer Portalでアプリを作成

1. https://developer.x.com/ にログイン(なければ開発者アカウント登録)
2. プロジェクトとアプリを新規作成
3. アプリの **「User authentication settings」** を開き、
   **「Read and Write」** 権限を有効化する
   (⚠️ 重要: デフォルトはRead onlyなので、必ずここを変更してから
   次のトークン発行を行うこと。権限変更前にトークンを発行していた場合は、
   権限変更後に再発行が必要)
4. **「Keys and tokens」** タブから以下の4つを取得する
   - API Key / API Key Secret (Consumer Keys)
   - Access Token / Access Token Secret(「Generate」ボタンから発行)

投稿(Write)のみであれば無料プランの範囲内で利用できるはずですが、
料金体系はX側で変更されることがあるため、最新の情報は
developer.x.com で確認してください。

### 2. GitHubリポジトリにSecretsを登録

リポジトリの **Settings → Secrets and variables → Actions →
New repository secret** から、以下の4つを登録する(名前は完全一致させる):

| Secret名 | 値 |
|---|---|
| `X_API_KEY` | API Key |
| `X_API_SECRET` | API Key Secret |
| `X_ACCESS_TOKEN` | Access Token |
| `X_ACCESS_TOKEN_SECRET` | Access Token Secret |

登録後は `.github/workflows/update.yml` が自動でこれらを読み込み、
新しい抽選回が追加された実行時にXへ投稿します。Secretsが未設定の間は
投稿だけスキップされ、データ取得・分析・コミットは通常通り行われます
(ログに「X API認証情報が未設定のため投稿をスキップします」と出ます)。

### 3. 重複投稿の防止について

`data/last_posted.json` に、ゲームごとに最後に投稿した回号を記録して
います。同じ回号のままワークフローが再実行されても再投稿はしません。
手動でもう一度投稿し直したい場合は、このファイルの該当ゲームの値を
削除するか回号を変更してからコミットしてください。

## ディレクトリ構成

```
src/
  config.py       # ロト6/ロト7のルールとデータ取得先URL
  fetch_data.py   # 当せん番号一覧のスクレイピング・正規化
  analyze.py      # 統計分析・レポート生成
  suggest.py      # 番号提案(当選確率は変わりません)
  post_to_x.py    # 傾向まとめをXへ自動投稿
tests/
  test_analyze.py     # 合成データによる分析ロジックのユニットテスト
  test_fetch_data.py  # 実際のHTML構造を模したサンプルでのパーステスト
  test_post_to_x.py   # 投稿文生成・重複投稿防止ロジックのテスト
data/             # 正規化済みの当せん番号CSV・投稿済み回号 (Actionsが自動更新)
reports/          # 生成されたレポート (Actionsが自動更新)
.github/workflows/
  update.yml      # 定期データ取得・分析ワークフロー
  ci.yml          # プッシュ時にテストを実行するCI
```

## テスト

```bash
pytest -q
```

実データではなく合成データ(乱数生成した仮想の当選番号)を使って、
集計ロジックが正しく動くことを検証しています。
