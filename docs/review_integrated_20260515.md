# 統合レビューレポート — invest-alpha-os システム品質診断

**作成日**: 2026-05-15
**main HEAD**: `2df9f9a`（R6.12-B docs）
**テスト件数**: 675件 全通過
**レビュー元**: Claude Code（技術詳細）+ claude.ai チャット（戦略観点）

---

## 0. Phase 1a 達成状況の確認（最重要）

### 問い: `alpha-os signals` で日本株 watchlist の momentum signals + Veto 結果が出るか？

**答え: ✅ Yes — 達成済み**

以下の実行で確認済み：

```
$ alpha-os signals --source cache-only --format markdown

## Momentum Signals — JP Watchlist
| # | Code | Sv2 | Labels | r5 | r20 | r60 | HiDist | VolR | Veto |
| 1 | 5802 | 6 | positive_20d_60d_momentum | +3.4% | +28.2% | +32.4% | -3.9% | 0.66x | — |
| 2 | 6506 | 5 | ... | ... | ... | ... | ... | ... | — |
| 3 | 5801 | 4 | ... | ... | ... | ... | ... | ... | ⚠ hard_momentum_overheat, fomo_chase_warning |
| 4 | 285A | 4 | ... | ... | ... | ... | ... | ... | ⚠ hard_momentum_overheat, fomo_chase_warning |
```

- `veto_status: "ok"` を返す
- `veto_result` が各銘柄行に付与される
- `285A`（Kioxia Holdings / 4文字英数字コード）が正常に処理される
- Markdown 表形式・JSON 形式どちらも出力可能

**Phase 1a コア機能（signals + Veto）は R6.8-B 時点で達成されている。**
達成確認 commit: `e1005be`（R6.8-B / 2026-05-14）

---

## 1. 技術品質ダブルチェック結果（Claude Code 実施）

### 🔴 エラーリスク（動作に影響する問題）

#### [T-1] `fomo_chase_warning` と `fomo_volume_price_chase` の条件重複による二重発火（**最重要**）

**場所**: `config/veto_rules.yaml` + `src/invis_alpha_os/risk/veto_rules.py`

**実証済みの問題**:

| 銘柄 | r5 | volume_ratio_25d | 発火ルール |
|---|---|---|---|
| `5801` | +20.7% | 0.51x（3.0倍未満） | `⚠ hard_momentum_overheat, fomo_chase_warning` |
| `285A` | +18.4% | 0.57x（3.0倍未満） | `⚠ hard_momentum_overheat, fomo_chase_warning` |
| `6501` | **-15.8%（急落）** | 1.56x | **`⚠ fomo_chase_warning`（急落銘柄に誤発火）** |

`6501` は6501円が急落した銘柄であるにもかかわらず、`fomo_chase_warning`（急騰追随・高値掴み警戒ルール）が発火している。これは `price_spike_5d = abs(r5)` つまり**絶対値**を使うため方向性が無視されているため。

**発火条件の整理**:

| ルール | 発火条件 | 問題 |
|---|---|---|
| `fomo_chase_warning` | `abs(r5) >= 0.15`（15%） | 急落でも発火。FOMO の意味とずれる |
| `fomo_volume_price_chase` | `r5 > 0.15` かつ `volume_ratio >= 3.0` | 正しく上昇+出来高限定 |

`fomo_volume_price_chase` が発火する条件は、すべて `fomo_chase_warning` の発火条件を内包している（= 二重発火が常に起きる）。

**現在の Markdown 出力例（r5=0.20, vol_ratio=3.5）**:
```
⚠ fomo_chase_warning, fomo_volume_price_chase
```

**修正案**:

- **案A（推奨）**: `fomo_chase_warning` の `metric` を `price_spike_5d` から削除または閾値を引き上げる（例: 0.30 以上）。`fomo_volume_price_chase` との住み分けを明確化する。
- **案B**: `fomo_chase_warning` を `veto_rules.yaml` から削除し、`fomo_volume_price_chase` に一本化する（急落誤発火もなくなる）。
- **案C（現状維持）**: 二重発火を「警戒強度の累積」として許容し、ドキュメントに記載する。

---

### 🟡 品質課題（動作はするが設計上の懸念）

#### [T-2] `risk/__init__.py` のエクスポート不完全

**場所**: `src/invis_alpha_os/risk/__init__.py`

```python
# 現在: format_veto_table_cell, momentum_breakdown_veto_context が __all__ に未記載
from .veto_rules import VetoEngine
__all__ = ["VetoEngine"]
```

`from invis_alpha_os.risk import format_veto_table_cell` は現在 `ImportError` になる。CLI・daily report は `from invis_alpha_os.risk.veto_rules import ...` と直接モジュールパスで import しているため動作するが、パッケージの公開 API として不整合。

**修正案（1行）**:
```python
from .veto_rules import VetoEngine, format_veto_table_cell, momentum_breakdown_veto_context
__all__ = ["VetoEngine", "format_veto_table_cell", "momentum_breakdown_veto_context"]
```

---

#### [T-3] CLI の `_veto_context` ローカル関数が冗長なラッパー

**場所**: `src/invis_alpha_os/cli/main.py` L364–365

```python
def _veto_context(m: Any) -> dict[str, float]:
    return momentum_breakdown_veto_context(m)  # 単純ラッパー
```

削除して `momentum_breakdown_veto_context(m)` を直接呼べばよい。**動作上の問題はない**が、将来の読者が混乱する可能性がある。

---

#### [T-4] `VetoEngine` インスタンス化の非対称性

| 箇所 | キャッシュ方式 |
|---|---|
| CLI `signals_command` | `VetoEngine(rules=load_yaml(...))` 毎回ロード |
| CLI `veto_command` | `VetoEngine(rules=load_yaml(...))` 毎回ロード |
| daily report `_momentum_veto_engine()` | `@lru_cache(maxsize=1)` でキャッシュ |

CLI は実行時 1 回呼ばれるだけなので性能問題はないが、設計の一貫性がない。

---

#### [T-5] `_momentum_veto_engine()` の `lru_cache` がテスト時にルール差し替えを阻む

**場所**: `src/invis_alpha_os/reports/momentum_daily.py` L30–37

`@lru_cache(maxsize=1)` で `VetoEngine` が固定されるため、テスト中に `veto_rules.yaml` を差し替えることができない。現在のテストは `MomentumBreakdown` のフィールド値で間接的に制御しており全通過しているが、将来ルールを差し替えるテストを書く場合は `_momentum_veto_engine.cache_clear()` が必要になる点を認識しておく必要がある。

---

### 🟢 技術面で正常確認済み

| 確認項目 | 結果 |
|---|---|
| `fomo_veto` セクションが `VetoEngine.evaluate()` で評価される | ✅ R6.8-E で修正済み |
| `VetoLevel.fomo_veto` が enum に存在する | ✅ R6.8-E で追加済み |
| `285A`（4文字英数字コード）が signals CLI で正常処理される | ✅ R6.6 で対応済み |
| `momentum_breakdown_veto_context` の合成ロジック（`fomo_volume_price_chase`） | ✅ r5>0 かつ vol>=3.0 の条件で 1.0/0.0 |
| `format_veto_table_cell` の `—` / `⚠ rule_id` 分岐 | ✅ |
| daily report の Veto 列が VetoEngine 経由で評価される | ✅ R6.8-C〜D で更新済み |
| GitHub Actions CI 直近 3 件 | ✅ 全 success |
| pytest 675 件 | ✅ 全通過 |

---

## 2. 戦略観点レビュー（claude.ai チャット 観察）

### 観察S-1: R6.6 → R6.12 の進行と Phase 1a の関係

| 期間 | コミット数 | 主な内容 |
|---|---|---|
| R6.6〜R6.8 | 約 15 件 | JP momentum signals + Veto 統合（Phase 1a コア） |
| R6.9〜R6.12 | 約 20 件 | US cache-only dry-run 系の積み上げ |

claude.ai チャットの懸念「Phase 1a 未達成のまま US 系が進んだのでは」については、**Phase 1a コア（JP signals + Veto + daily report Veto 列）は R6.8-B〜C 時点で達成されている**ことを Claude Code 側で確認済み。

ただし、claude.ai チャットが指摘した「人間の時間予算は有限」という点は有効。R6.10〜R6.12 の US dry-run 系は cache-only/fixture-only であり JP 機能への影響はないが、**日次レポートへの US セクション接続・実運用連携はまだ未達成**。

---

### 観察S-2: R6.9-A stale branch の分析

**ブランチ名**: `work/r6-9-a-veto-result-centralization-rebase`（origin に push 済み・未 merge）

**追加内容（diff で確認）**:

```python
# R6.9-Aが追加しようとしていた関数
def veto_hits_to_result_dict(hits: list[VetoResult]) -> dict[str, Any]:
    return {"triggered": ..., "count": ..., "rules": [...]}

def build_momentum_veto_result(m: Any, engine: VetoEngine) -> dict[str, Any]:
    return veto_hits_to_result_dict(engine.evaluate(momentum_breakdown_veto_context(m)))
```

**評価**: R6.9-A が追加しようとしていた `veto_hits_to_result_dict` と `build_momentum_veto_result` は**有効な共通化**。現在 CLI の `_veto_row()` で同等のロジックがインライン実装されており、この共通化を適用すれば `_veto_row()` が削除できる。

**stale 化の推定原因**: R6.9-A の時点では `momentum_breakdown_veto_context` や `format_veto_table_cell` が `veto_rules.py` に存在しなかった。R6.8-E〜F でこれらが追加された後、R6.9-A を rebase すれば素直に適用できると考えられる。

**推奨**: R6.9-A の `veto_hits_to_result_dict` + `build_momentum_veto_result` を main に取り込むことで、CLI の `_veto_row()` インライン実装を削除できる。[T-3] の `_veto_context` 冗長問題とともに解消できる。

---

### 観察S-3: US dry-run 系の戦略的位置づけ

R6.10〜R6.12 の US 系コンテンツ（cache-only dry-run / universe / multi-symbol renderer）は、現時点では daily report に未接続。

```
docs に記載の「未接続」文言（R6.11-D, G, H, R6.12-A, B すべて同様）:
"live HTTP なし · production cache write なし · report / Veto / portfolio / macro 未接続"
```

これらは **開発用プリミティブの積み上げ**であり、実際にユーザーが触れる出力への接続はまだない。JP 日次レポートとの統合順位を明確にする必要がある。

---

### 観察S-4: 5/12 レビュー（claude.ai）指摘の現状確認

| 5/12 指摘 | 現状 | 状態 |
|---|---|---|
| Critical-1: 285A が `unsupported_code` で skip された | R6.6 で修正済み。signals + daily report 両方で正常処理 | ✅ 解決済み |
| Critical-2: signals 実装ゼロ | R6.8-B で signals CLI + Veto 統合完了 | ✅ 解決済み |
| High-2: `invest-alpha-os` vs `invis_alpha_os` 名前不一致 | パッケージ名は `invis_alpha_os` で維持（renaming 禁止ルール）。CLI コマンド名は `alpha-os` | ⚠ 名前不一致は継続（仕様として受容） |

---

## 3. ChatGPT へのフィードバック — 修正優先順位

### 優先度 HIGH：今すぐ修正を検討すべき

#### [F-1] `fomo_chase_warning` の誤発火解消（`veto_rules.yaml` のみ変更）

**問題**: 急落銘柄（`6501`: r5=-15.8%）に `fomo_chase_warning`（FOMO 警戒）が発火している。`price_spike_5d = abs(r5)` により方向性を無視しているため。

**推奨修正（案B: 最小変更）**: `fomo_chase_warning` を削除し、`fomo_volume_price_chase` に一本化する。

```yaml
# 現在
fomo_veto:
  - id: "fomo_chase_warning"      # ← 削除推奨（誤発火）
    metric: "price_spike_5d"
    threshold: 0.15
    message: "Possible FOMO chase setup"
  - id: "fomo_volume_price_chase" # ← 残す（正しい複合条件）
    metric: "fomo_volume_price_chase"
    threshold: 1.0
    message: "Volume vs 25d prior avg >= 3.0 with r5 > 15% (chase caution)"
```

変更後の期待動作:
- `6501`（急落）→ Veto 列が `—` になる（FOMO 誤発火なくなる）
- `5801`・`285A`（急騰 + overheat）→ `⚠ hard_momentum_overheat` のみ（volume_ratio が 3.0 倍未満のため `fomo_volume_price_chase` は不発）

#### [F-2] `risk/__init__.py` へのエクスポート追加（1行変更）

```python
# src/invis_alpha_os/risk/__init__.py
from .veto_rules import VetoEngine, format_veto_table_cell, momentum_breakdown_veto_context
__all__ = ["VetoEngine", "format_veto_table_cell", "momentum_breakdown_veto_context"]
```

---

### 優先度 MEDIUM：次のリファクタリング機会に対応

#### [F-3] R6.9-A の `build_momentum_veto_result` / `veto_hits_to_result_dict` を取り込む

`work/r6-9-a-veto-result-centralization-rebase` ブランチに存在する 2 関数を `veto_rules.py` に追加し、CLI の `_veto_row()` インラインロジックを削除する。

対象ファイル:
- `src/invis_alpha_os/risk/veto_rules.py`: 2 関数追加
- `src/invis_alpha_os/cli/main.py`: `_veto_row()` と `_veto_context()` を削除、`build_momentum_veto_result` を使用

#### [F-4] CLI の `_veto_context` ローカル関数削除（[F-3] に含めて対応）

単純ラッパー関数を削除し、直接 `momentum_breakdown_veto_context(m)` を呼ぶ。

---

### 優先度 LOW：将来の保守性向上のため

#### [F-5] `VetoEngine` インスタンス化の一貫性確保

CLI 側も `@lru_cache` または関数スコープ外での初期化にする（現在は daily report のみキャッシュあり）。

---

## 4. 次の推奨タスク（Phase 1a 完了後の優先順）

以下は **JP daily report の実運用直結タスクを優先**とした順序。

| 優先 | タスク | 説明 |
|---|---|---|
| 1 | [F-1] `fomo_chase_warning` 誤発火修正 | `veto_rules.yaml` のみ変更。テスト 1〜2 件追加 |
| 2 | [F-2] `risk/__init__.py` エクスポート追加 | 1行変更。リスクゼロ |
| 3 | [F-3] R6.9-A `build_momentum_veto_result` 取り込み | CLI コードの重複解消 |
| 4 | daily report への US セクション接続（R6.12-C 以降） | US dry-run renderer を日次レポートに接続 |
| 5 | `veto_rules.yaml` 拡充（R6.8-D: `soft_volume_spike_extreme`、閾値 5.0 倍） | 設計ドキュメント `docs/16` に方針あり |

**やらないこと（現時点）**:
- live HTTP 接続
- production cache write
- Gmail / PDF 配信
- portfolio allocation
- macro regime 接続

---

## 5. 開発ベロシティの評価（claude.ai 観察への回答）

claude.ai チャットが懸念した「R6.6 → R6.12 で 6 段階進んだのに Phase 1a 未達成では？」は、**Phase 1a コア機能（signals + Veto）は R6.8-B で達成済み**のため、懸念の前提が実際とは異なる。

ただし以下は claude.ai チャットの指摘通り有効：

1. **US dry-run 系は daily report に未接続のまま**。`docs/` に「report 未接続」の文言が R6.11-D〜R6.12-B の全コミットに共通する。実ユーザー出力には繋がっていない。

2. **R6.9-A が stale 化している**。Veto の共通化（`build_momentum_veto_result`）は有効な整理で、現在 CLI にインラインで重複実装されている。

3. **`fomo_chase_warning` の誤発火**（急落銘柄への FOMO 警戒発火）は、現在の実出力に直接影響しており、信頼性に影響する。

---

## 付録: 変更が必要なファイル一覧（ChatGPT 作業用）

| ファイル | 変更内容 | 優先度 |
|---|---|---|
| `config/veto_rules.yaml` | `fomo_chase_warning` 削除または閾値引き上げ | HIGH |
| `src/invis_alpha_os/risk/__init__.py` | `format_veto_table_cell` / `momentum_breakdown_veto_context` を `__all__` に追加 | HIGH |
| `src/invis_alpha_os/risk/veto_rules.py` | `veto_hits_to_result_dict` / `build_momentum_veto_result` 追加（R6.9-A 内容） | MEDIUM |
| `src/invis_alpha_os/cli/main.py` | `_veto_context` / `_veto_row` のインライン削除、共通関数使用 | MEDIUM |
| `tests/test_veto_rules.py` | `fomo_chase_warning` 削除後の整合テスト更新 | HIGH（[F-1]対応時） |
| `tests/test_momentum_signals.py` | veto_result の期待値更新（`fomo_chase_warning` 削除後） | HIGH（[F-1]対応時） |
