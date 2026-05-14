# R6.8-D 設計ドキュメント — `veto_rules.yaml` 出来高急増ルール追加

**ステータス**: 設計中（未実装）
**作成**: 2026-05-14
**対象ブランチ**: `work/r6-8-d-veto-rules-design`

---

## 1. 目的

`veto_rules.yaml`（拒否・警戒ルール設定ファイル）に、25日平均比の出来高倍率（`volume_ratio_25d`）を基にした `soft_veto`（弱い警戒判定）ルールを追加する。

対象シグナル: `volume_ratio_25d >= 3.0`（25日平均比で出来高が3倍以上）

---

## 2. 調査結果

### 2.1 現在の `veto_rules.yaml` 構成

```yaml
hard_veto:
  - id: "hard_market_heat"       # 市場過熱スコア >= 0.9
  - id: "hard_momentum_overheat" # overheat_flag >= 1.0

soft_veto:
  - id: "soft_valuation_stretch" # バリュエーション伸長 >= 0.65

fomo_veto:
  - id: "fomo_chase_warning"     # price_spike_5d >= 0.15
```

### 2.2 VetoEngine の評価ループ（重要な既存ギャップ）

`src/invis_alpha_os/risk/veto_rules.py` の `evaluate()` メソッドは以下のループで動作：

```python
for level_name in ("hard_veto", "soft_veto"):  # fomo_veto は評価されていない
```

**`fomo_veto` セクションは現在完全に無視されている。** これはR6.8-A以前からの既存ギャップ。

### 2.3 `_veto_context` の現在のマッピング（CLI）

`src/invis_alpha_os/cli/main.py` の `_veto_context()` 関数：

```python
def _veto_context(m: Any) -> dict[str, float]:
    return {
        "price_spike_5d": abs(m.r5 or 0.0),
        "overheat_flag": 1.0 if m.overheat_flag else 0.0,
    }
```

**`volume_ratio_25d` はコンテキストに含まれていない。** `soft_volume_spike` ルールを追加しても、このマッピングを更新しない限り評価されない。

### 2.4 `volume_spike` と `volume_ratio_25d` の関係

`src/invis_alpha_os/signals/momentum.py`:

```python
def detect_volume_spike(volumes, *, multiplier=3.0, lookback=25):
    # 最新出来高 >= 3.0 × 直近25日平均（直近バー除外）→ True
```

```python
def volume_ratio_25d_prior_mean(volumes):
    # 最新出来高 / 直近25日平均（直近バー除外）→ float
```

`volume_spike=True` は `volume_ratio_25d >= 3.0` と**等価**（同一の閾値3.0倍、同一の計算ウィンドウ）。

`MomentumBreakdown` には両方のフィールドが存在：
- `volume_spike: bool`
- `volume_ratio_25d: float | None`

### 2.5 daily report の `_veto_cell` の現在の動作

`src/invis_alpha_os/reports/momentum_daily.py` の `_veto_cell()` は `overheat_flag` のみを参照しており、**`soft_veto` の結果を表示しない**。

`soft_volume_spike` ルールを追加しても、`_veto_cell` を変更しない限り daily report（日次レポート）には反映されない。

---

## 3. 提案するルール案

### 案A（基本案）: `volume_ratio_25d` をそのまま使用

```yaml
soft_veto:
  - id: "soft_valuation_stretch"
    metric: "valuation_stretch"
    threshold: 0.65
    message: "Valuation stretch exceeds soft threshold"
  - id: "soft_volume_spike"
    metric: "volume_ratio_25d"
    threshold: 3.0
    message: "Volume spike: 25d-avg ratio >= 3.0 (possible FOMO chase)"
```

**メリット**: 連続値（例: 4.2x）を評価できる。閾値の調整が設定ファイルのみで完結する。

**デメリット**:
- `_veto_context` に `volume_ratio_25d` の追加が必要（実装変更）
- `volume_ratio_25d` が `None` の場合、`float(context.get("volume_ratio_25d", 0.0))` → 0.0 となり不発火（安全側に倒れる）
- `volume_spike=True` の銘柄と完全に重複するため、既存の `volume_spike` ラベルとの整合性の説明が必要

### 案B: `volume_spike` のBoolean → float マッピングを使用

`_veto_context` に以下を追加：

```python
"volume_spike_flag": 1.0 if m.volume_spike else 0.0,
```

```yaml
soft_veto:
  - id: "soft_volume_spike"
    metric: "volume_spike_flag"
    threshold: 1.0
    message: "Volume spike: latest volume >= 3x 25d prior average"
```

**メリット**: `volume_spike` との整合性が明確。Noneを考慮不要。

**デメリット**: `threshold: 1.0` という書き方が `hard_momentum_overheat` と同一形式になり、`soft_veto` として設定ファイルを見たときに閾値の意味が不明瞭。

### 案C（推奨）: 閾値を引き上げて過検知を抑制

```yaml
soft_veto:
  - id: "soft_volume_spike_extreme"
    metric: "volume_ratio_25d"
    threshold: 5.0
    message: "Extreme volume spike: 25d-avg ratio >= 5.0 (high FOMO risk)"
```

**メリット**:
- 3.0倍（`volume_spike=True`）より高い水準のみを警戒対象とするため、過検知リスクを大幅に削減
- キャッシュデータでの実発火銘柄数が少なく、シグナルとしての価値が高い
- 同じく `_veto_context` への追加が必要だが、発火条件が絞られる

**デメリット**: 閾値の根拠（5.0倍）がデータで検証されていない

---

## 4. 過検知リスクの分析

### 4.1 方向性の欠落

`volume_ratio_25d >= 3.0` は上昇・下落を問わず発火する。

- `r5 > 0` かつ `volume_spike=True` → FOMO追随リスク（警戒根拠あり）
- `r5 < 0` かつ `volume_spike=True` → 急落出来高急増（警戒根拠が異なる）
- `r5 ≈ 0` かつ `volume_spike=True` → 横ばいで異常出来高（ノイズ可能性大）

`VetoEngine` は現在複合条件（AND条件）を評価できない。単一メトリクス×閾値のみ。

### 4.2 現在のキャッシュデータでの推定発火率

既存の `volume_spike=True` 銘柄の割合は `ranked` の上位に集中する傾向がある（モメンタムスコアに `volume_ratio_25d_hot` スコアが加算されるため）。

3.0倍閾値のまま採用すると、**上位ランク銘柄の多くに `⚠ soft_volume_spike` が表示される可能性がある**（= シグナルの希薄化）。

### 4.3 既存の `fomo_chase_warning` との重複

`fomo_veto` の `fomo_chase_warning` は `price_spike_5d >= 0.15`（5日リターン絶対値 >= 15%）を条件とする。
`VetoEngine` がこれを**現在評価していない**ため、実質的に機能していない（既存バグ）。

出来高急増ルールを `soft_veto` に追加する前に、`fomo_veto` の無視バグを対処するか、放置する方針を決める必要がある。

---

## 5. 実装が必要な場合の影響ファイル

| ファイル | 変更内容 | リスク |
|---|---|---|
| `config/veto_rules.yaml` | `soft_veto` にルール追加 | 低（設定ファイルのみ） |
| `src/invis_alpha_os/cli/main.py` | `_veto_context` に `volume_ratio_25d` 追加 | 中（テスト更新が必要） |
| `src/invis_alpha_os/reports/momentum_daily.py` | `_veto_cell` に soft veto対応を追加（任意） | 中（daily report（日次レポート）の列幅・表示が変わる） |
| `tests/test_veto_rules.py` | `soft_volume_spike` のユニットテスト追加 | 低 |
| `tests/test_momentum_signals.py` | CLI出力でのveto_result確認テスト追加 | 低〜中 |

`_veto_cell` の変更は**任意**。`soft_veto` はCLI JSON出力にのみ反映し、daily reportは `hard_veto` のみ表示とする分離設計も有効。

---

## 6. 設計上の未解決論点

以下は実装前に方針決定が必要：

### 論点1: `fomo_veto` の無視バグをどう扱うか

**選択肢A**: R6.8-D スコープ外として放置（`fomo_veto` セクションを削除してyamlを整理）

**選択肢B**: `VetoEngine` のループに `fomo_veto` を追加して修正（実装変更が必要）

**推奨**: R6.8-D では放置。`fomo_veto` の `price_spike_5d` は `_veto_context` にすでに含まれているため、`fomo_veto` → `soft_veto` に移動するだけで機能する。ただし既存テストへの影響確認が必要なため、別タスクとして独立させる。

### 論点2: `soft_veto` の表示範囲

- CLI JSONのみ: `veto_result.rules` に含まれる（現在の動作で自動対応）
- CLI Markdown: `--format markdown` の Veto列に `⚠ soft_volume_spike` を表示
- daily report: `_veto_cell` を拡張して soft vetoも表示（表示変更が伴う）

**推奨**: 当面はCLI JSON/Markdownのみに留め、daily report の `_veto_cell` は変更しない。理由: daily reportの列幅が固定でないため、短い記号（`⚠`）のみを示す場合は情報過多になる可能性がある。

### 論点3: `volume_ratio_25d` が `None` の場合の扱い

`VetoEngine` のデフォルトは `float(context.get(metric_key, 0.0))` = 0.0 → 閾値未達 → 不発火（安全側）。

これは意図した動作として明示的に文書化する必要がある。

---

## 7. 推奨アクション（優先順）

1. **R6.8-D実装前確認**: 案Cの閾値5.0倍を選択し、`_veto_context` と `veto_rules.yaml` の最小変更で実装する
2. **`fomo_veto` 無視バグ**: 別タスク（R6.8-E相当）として切り出し、`fomo_veto` セクション処理を `VetoEngine` に追加するか削除するかを決定する
3. **daily report の soft veto表示**: 別タスクとし、R6.8-Dの実装結果を見てから判断する

---

## 8. R6.8-D実装時の想定コミット構成（参考）

```
Main R6.8-D: Add soft_volume_spike veto rule (threshold 5.0x)
  - config/veto_rules.yaml: soft_volume_spike ルール追加
  - src/invis_alpha_os/cli/main.py: _veto_context に volume_ratio_25d 追加
  - tests/test_veto_rules.py: soft_volume_spike のユニットテスト追加
  - tests/test_momentum_signals.py: CLI veto_result テスト更新
```

`reports/momentum_daily.py` の変更は含まない（soft vetoはCLIのみに留める）。
