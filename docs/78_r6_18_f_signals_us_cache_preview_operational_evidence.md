# R6.18-F — Signals US cache preview operational evidence（operator）

**日付**: 2026-05-20 · **main 起点**: `9c6f5e5`（R6.18-E PR **#23**）  
**性質**: read-only smoke 記録 · **default enablement 未承認**

---

## 1. Purpose

- opt-in **`signals --us-cache-preview`** を安全に運用し、**証拠を蓄積**する
- default enablement 議論の前に **2+ 運用日**の read-only smoke を記録する
- **default はブロック**（[docs/75](./75_r6_18_bc_default_enablement_readiness_checklist.md)）

---

## 2. Current Scope

| 項目 | 状態 |
|---|---|
| `signals --us-cache-preview` | **opt-in only**（default **off**） |
| `signals` default | **変更なし**（JP momentum JSON/markdown のみ） |
| `daily` default | **変更なし** |
| live HTTP / cache write | **禁止**（本手順では実行しない） |
| cache JSON commit | **禁止** |
| scoring / ranking / recommendation | **禁止** |
| portfolio / macro / Veto | preview に **接続なし** |

**出力契約**（preview のみ）: symbol · latest_date · freshness_status · close · return_1d/5d/20d · volume_status · note — 詳細 [docs/74](./74_r6_18_bc_cache_only_connection_design.md) §5。

---

## 3. Read-Only Smoke Procedure

リポジトリ root · venv 推奨。秘密はログに出さない。

### 3.1 Inventory（任意 · read-only）

```bash
.venv/bin/python -m invis_alpha_os.cli.main debug us-daily-bars-cache-inventory \
  --cache-root outputs/market_data/us_daily_bars \
  --format markdown
```

### 3.2 Signals default（preview なし）

```bash
.venv/bin/python -m invis_alpha_os.cli.main signals --dry-run
```

**確認**:

- stdout が JSON の場合: トップレベルに **`us_cache_preview` キーが無い**
- Markdown の場合: **`### US Cache Preview (opt-in)` が無い**

### 3.3 Signals opt-in（JSON · 推奨 smoke）

```bash
.venv/bin/python -m invis_alpha_os.cli.main signals --dry-run --us-cache-preview
```

**確認**:

- JSON に **`us_cache_preview`** オブジェクトあり（`status` · `rows` 等）
- preview 行に allowed 列のみ
- preview 節相当テキストに **forbidden terms なし**（buy/sell/recommendation/allocation/portfolio/veto/macro/production 等）
- **live HTTP なし** · **cache write なし**

### 3.4 Signals opt-in（Markdown）

```bash
.venv/bin/python -m invis_alpha_os.cli.main signals --dry-run --us-cache-preview --format markdown
```

**確認**:

- JP momentum 表の後に **`### US Cache Preview (opt-in)`** 節が追記される
- forbidden terms は **preview 節のみ**を検査（momentum 表の Veto 列は従来どおり · preview 契約外）

### 3.5 Edge path: `--bars-file` + opt-in

```bash
# 例: 既存 fixture を利用する場合
.venv/bin/python -m invis_alpha_os.cli.main signals \
  --bars-file tests/fixtures/us_equities/msft_25bars_metrics_envelope.json \
  --code MSFT \
  --us-cache-preview
```

**注意（R6.18-E 仕様）**:

- この経路は **JSON のみ** `us_cache_preview` を付与する
- **Markdown preview 節は未対応**（通常 watchlist 経路で `--format markdown` を使用）

### 3.6 Daily 回帰（任意）

```bash
env -u JQUANTS_API_KEY -u JQUANTS_ENABLED -u JQUANTS_ALLOW_LIVE_HTTP -u JQUANTS_API_BASE_URL \
  .venv/bin/python -m invis_alpha_os.cli.main daily
```

preview 節なし。opt-in は [docs/69](./69_r6_17_b_opt_in_us_cache_preview_runbook.md) §4.3。

---

## 4. Evidence Table（operator が記入）

**2 行以上** · **異なる運用日**で記録してから default 議論に入る。

| date | main commit | command | default excludes preview | opt-in includes preview | live HTTP absent | cache write absent | forbidden terms absent (preview only) | stale / fresh_enough | tests/CI | operator note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| _pending_ | | `signals --dry-run` | | | | | | | | |
| _pending_ | | `signals --dry-run --us-cache-preview` | | | | | | | `test_us_cache_preview_opt_in` / Actions | |

---

## 5. Default Enablement Gate

Default enablement **は未承認**。以下を **すべて** 満たすまで PR を起票しない:

- 上記 evidence **2+ 運用日**
- inventory: **fresh_enough 16 / stale 0**（判断時点）
- forbidden terms なし · live HTTP/cache write なし
- output contract 安定 · CI pass
- Codex read-only review · default 変更時は Claude architecture review
- rollback 現行 · **operator 明示承認**

---

## 6. Stop Conditions

以下のいずれかで **default 検討を停止**:

- stale > 0 または freshness_unknown > 0
- signals default 出力が変わった（`us_cache_preview` が無フラグで出現 等）
- preview に forbidden trading terms
- live HTTP / cache write 経路の実行
- cache JSON のコミット
- CI / 関連テスト失敗

---

## 7. Next Phase Candidates

| 候補 | 内容 |
|---|---|
| **R6.18-G** | 本 doc §4 に **2+ smoke 行**を記入（read-only のみ） |
| **R6.18-H** | default enablement review package（**G 完了後** · 別承認） |
| **継続** | opt-in 手動運用のまま default を延期 |

---

## 8. 関連

- 実装: [docs/77](./77_r6_18_e_b1_signals_us_cache_preview.md)
- Daily runbook: [docs/69](./69_r6_17_b_opt_in_us_cache_preview_runbook.md)
- Readiness: [docs/75](./75_r6_18_bc_default_enablement_readiness_checklist.md)
- Smoke Longpack draft: [.agent/r6_18_g_signals_preview_smoke_evidence_longpack_draft.md](../.agent/r6_18_g_signals_preview_smoke_evidence_longpack_draft.md)
