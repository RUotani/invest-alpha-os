# Decision — Early Discovery Operational Definition

## 3行サマリー

- Early Discoveryは、テーマ初動/加速、相対強度改善、出来高の低位反転、過熱なし、portfolio gate通過を同時に確認する。
- 高モメンタム上位や急騰済みテーマ代表をEarly Discoveryへ入れない。Early Discoveryが空でもよい。
- 現在のfixture出力はロジック検証用であり、運用成績や将来リターンの証拠ではない。

## 定義

Early Discoveryは、次の条件を満たす候補である。

1. theme phaseが `Early` または `Acceleration`
2. candidateが既にhard overheatではない
3. relative strengthが低位/base状態から改善している
4. volumeが低位/base状態から反転している
5. portfolio gateが新規リスクを抑制していない

Early Discoveryは、次を意味しない。

- 大幅上昇後の高モメンタム
- 直近リターン上位
- 既に過熱したテーマリーダー
- Early Discoveryが空のときの強制的な代替候補

## Observable Variables

| Variable | 意味 | 現在地 |
|---|---|---|
| `ret_n` | 指定期間の価格変化 | fixture/cache-only |
| `ma_deviation` | 移動平均からの乖離 | fixture/cache-only |
| `rs_acceleration` | benchmark比の相対強度改善 | fixture-only skeleton |
| `volume_inflection` | 低位/base出来高からの反転 | fixture-only skeleton |
| `theme_phase` | Early / Acceleration / Overheat等 | #508 |
| `portfolio_cash_ratio` | 現金比率gate | #508 / fixture context |
| `single_stock_ratio` | 個別株比率gate | #508 / fixture context |

## Data Availability

- 現在: fixture/cache-only。nullable入力を維持し、不明値を捏造しない。
- 将来承認対象: read-only price/volume接続。
- 将来検討: fundamentals、analyst revisions、theme flows。
- Hard Gate: live fetch、cache write、broker、import、trading、secret表示は未承認。

## 285A Treatment

- `285A` は Theme Proxy / Do Not Chase。
- hard overheatのためEarly Discoveryではない。
- 周辺・出遅れ候補の探索起点として扱う。

## Provisional Scoring

v1.5 fixture scoreは、recent return、MA deviation、volume inflection、RS accelerationを暫定重みで結合する。
重みは未較正であり、分類性能・投資成績・将来リターンを示さない。hard overheatまたはportfolio gateは、scoreが存在してもEarly Discovery分類を抑制する。

## Safety

この定義は候補発見ロジックのfixture検証用であり、売買指示、注文、価格目標、performance evidenceではない。
