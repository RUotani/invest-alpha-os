# R6.17-B — Opt-in US cache preview runbook（operator · docs-only）

**ステータス**: **ブランチ作業のみ**（**`main` 未反映**）。ブランチ: **`work/r6-17-b-opt-in-preview-runbook`**。  
**前提**: R6.17 implementation on **`main`**（`879fe47` / PR **#16**）· smoke **[docs/68](./68_r6_17_a_opt_in_us_cache_preview_smoke.md)**。

---

## 1. 目的

- **`daily --us-cache-preview`** を operator が **明示 opt-in** で使う手順を固定する
- **observation-only** · **trading recommendation ではない**
- **default daily は変更しない**（preview 節はフラグ時のみ）
- **stale** を警告として表示し、returns を signal input から分離する
- **live HTTP / cache write** は本 runbook では **実行しない**

---

## 2. 非目的

- stale 3 symbols の **自動 / 一括 refresh**（別 Longpack · 別承認）
- **default enablement**（`market_data.yaml` 等）
- product code · workflow · Makefile · `pyproject` 変更
- Veto / portfolio / macro 接続

---

## 3. 実行前チェック

| チェック | 期待（2026-05 時点の参考） |
|---|---|
| `origin/main` 最新 | R6.17 + R6.17-A docs 取り込み済み |
| cache_root 存在 | `outputs/market_data/us_daily_bars/`（**gitignore**） |
| inventory read-only | ok **16** · missing **0** · fresh_enough **13** · stale **3** |
| secrets | **`.env` 内容をログ・コミットに載せない** |
| 承認 | 本手順は **read-only** のみ |

**参考 stale symbols**: **MSFT** · **GOOGL** · **GLDM**（古い bar / fixture 由来 · preview では `stale — returns not used`）

---

## 4. 実行手順（read-only）

CLI 詳細は `python -m invis_alpha_os.cli.main <command> --help` を参照。パスはリポジトリ root 相対。

### 4.1 Inventory（必須 · read-only）

```bash
python -m invis_alpha_os.cli.main debug us-daily-bars-cache-inventory \
  --cache-root outputs/market_data/us_daily_bars \
  --format markdown
```

JSON 要約が必要なら `--format json`。**HTTP なし · cache write なし**。

### 4.2 Default daily（preview 節が出ないこと）

```bash
# JQUANTS_* が .env にある場合は誤判定を避けるため unset 推奨
env -u JQUANTS_API_KEY -u JQUANTS_ENABLED -u JQUANTS_ALLOW_LIVE_HTTP -u JQUANTS_API_BASE_URL \
  python -m invis_alpha_os.cli.main daily
```

**確認**: 出力 Markdown に **`### US Cache Preview (opt-in)` が無い**こと。

### 4.3 Opt-in daily（preview 節あり）

```bash
env -u JQUANTS_API_KEY -u JQUANTS_ENABLED -u JQUANTS_ALLOW_LIVE_HTTP -u JQUANTS_API_BASE_URL \
  python -m invis_alpha_os.cli.main daily --us-cache-preview
```

**確認**（preview 節のみ）:

| 項目 | 期待 |
|---|---|
| 見出し | `### US Cache Preview (opt-in)` |
| 列 | symbol · latest_date · freshness_status · close · return_1d · return_5d · return_20d · volume_status · note |
| stale 行 | note = **`stale — returns not used`** |
| aggregate score | **算出なし**（disclaimer: “No aggregate score.”） |
| forbidden terms | buy · sell · recommendation · allocation · portfolio · veto · macro · production — **節内に無し** |
| live_http | **false** |

出力先: `outputs/reports/daily/{JST-date}.md`（**gitignore**）。

---

## 5. Stale symbol handling（運用方針）

| Symbol | 扱い |
|---|---|
| MSFT · GOOGL · GLDM | preview **に行は出る** · `freshness_status=stale` · returns は **判断材料として表示するが scoring 入力ではない** |

- **許容**: stale 行を残したまま opt-in preview を運用（警告として読む）
- **非許容（別作業）**: stale を無視して production decision に使う
- **refresh**: 下記 §6 · **本 runbook では実行しない**

---

## 6. Stale refresh plan（別承認 · 未実行）

**目的**: fresh_enough **13 → 16** · stale **3 → 0**（目標）。

| Step | 内容 | 承認 |
|---|---|---|
| 1 | 対象: **MSFT** · **GOOGL** · **GLDM** のみ | operator |
| 2 | per-symbol: `debug us-provider-cache-preview --live`（**no write**）→ `preview_ok` / shape 確認 | **CONFIRM_US_LIVE_HTTP=YES** 等 · [docs/56](./56_r6_15_c_us_cache_population_runbook.md) / [docs/61](./61_r6_16_c_operator_gated_ingest_design.md) |
| 3 | per-symbol: `--write-cache` + 二重ゲート | **CONFIRM_US_CACHE_WRITE=YES** |
| 4 | after: `debug us-daily-bars-cache-inventory`（read-only） | — |
| 5 | opt-in `daily --us-cache-preview` で stale note 解消確認 | read-only |

**禁止**: 本計画を **この PR / この runbook 実行と同時に自動化しない**。専用 **Longpack** で実施。

---

## 7. Default enablement policy

| 項目 | 状態 |
|---|---|
| R6.17 preview | **opt-in only**（`--us-cache-preview`） |
| `include_us_momentum_cache_only_section` | **default false**（変更しない） |
| default に preview を載せる | **別承認** · ChatGPT / ユーザー |

**default enable 前の推奨ゲート**:

1. `stale_count == 0` **または** stale 残存を運用方針として文書化済み
2. 本 runbook + [docs/68](./68_r6_17_a_opt_in_us_cache_preview_smoke.md) レビュー済み
3. live HTTP / cache write ポリシー確認
4. （任意）Codex PR review · Claude arch review（default 変更時）

---

## 8. 関連ドキュメント

- [docs/70_r6_17_c_operational_readiness.md](./70_r6_17_c_operational_readiness.md)
- [docs/71_r6_17_c_stale_refresh_approval_package.md](./71_r6_17_c_stale_refresh_approval_package.md)
- [docs/72_r6_17_c_default_enablement_checklist.md](./72_r6_17_c_default_enablement_checklist.md)
- [docs/65_r6_17_opt_in_us_cache_preview_plan.md](./65_r6_17_opt_in_us_cache_preview_plan.md)
- [docs/67_r6_17_opt_in_us_cache_preview_implementation.md](./67_r6_17_opt_in_us_cache_preview_implementation.md)
- [docs/68_r6_17_a_opt_in_us_cache_preview_smoke.md](./68_r6_17_a_opt_in_us_cache_preview_smoke.md)
- [docs/62_r6_16_d_us_cache_full_population_status.md](./62_r6_16_d_us_cache_full_population_status.md)
