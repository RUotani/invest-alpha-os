# v82 Target Allocation Gap Calculator

Date: 2026-06-02

## 背景

v78 の redacted portfolio context が週次レポートに反映され、現金比率の制約や個別株比率の目安が「前提」として読めるようになった。
一方で、観測時点の現在配分と、目標配分（現金 30%、株式 49%、オルタナ 10.5%、債券 10.5%、個別株 10〜15%）との差分が数値として明示されていない。

そのため、週次判断で「現金回復を優先する理由」と「何がどれだけズレているか」を、読み手が短時間で検証しづらい。

## 目的

weekly candidate brief / email preview に、現在配分と目標配分の差分（配分ギャップ）を計算して表示し、
現金・株式系・個別株・債券・オルタナの過不足を可視化する。

本差分は「売買指示」ではなく、観測・検証・整理優先度づけのための数値根拠として利用する。

## 追加した機能（v82）

1. `目標配分との差分を計算する calculator` を追加
2. 現金 15% / 20% / 30% それぞれへの不足額を計算
3. 株式系 67.8% vs 49.0% の over/under 判定
4. 個別株 19.6% vs 10〜15% band の above-band 判定
5. 債券 13.5% vs 10.5% の判定
6. GOLD + 仮想通貨・高ベータ + レバ（暫定オルタナ）: 7.0% vs 10.5% の below-target 判定
7. Markdown 出力（weekly report copy-ready 内の短縮版）
8. email preview には 3 行要約を追加
9. tests と decision doc を追加

## Safety Boundary

この milestone は source-only の観測・検証用表示であり、取引実行には触れない。

明示的に含めない：

- workflow 変更 / `.github/workflows` 変更
- provider live HTTP / market-data live fetch
- cache write / cache directory creation
- actual refresh/import / manual actual import
- broker API / broker login
- raw broker export parsing / raw broker data persistence
- raw OHLCV/API persistence / raw Excel direct parsing
- reports-private raw data write / Git-tracked raw data write
- env/secret 表示
- dependency / pyproject / Makefile 変更
- trading action / order placement
- automated buy/sell execution recommendation

## 影響範囲

- `src/invis_alpha_os/portfolio/` に v82 calculator 追加
- `weekly_candidate_brief`（copy-ready ブロック）に `## 目標配分ギャップ（v82）` を追加
- `weekly_candidate_brief_email` に 3 行要約を追加
- tests / decision doc 追加

## 反証（bear case）

- 目標配分ギャップの表示が、読み手に「売買判断」と誤読される可能性がある。
  → 対策として、本文に「売買指示ではない」文言を明示し、用語も観測・整理用途に寄せる。

- 暫定オルタナの合成が、将来 portfolio context の定義とズレる可能性がある。
  → 対策として、 calculator は portfolio context 文字列の parse により差分計算を行う。

## 次のアクション

1. v86 scheduled run など、次の週次 artifact で v82 出力が期待どおり反映されるか観測する。
2. 誤読防止の UX が不十分なら、email preview の 3 行要約表現を微修正する。

