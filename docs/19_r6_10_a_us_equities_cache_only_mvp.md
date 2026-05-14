# R6.10-A — US equities cache-only MVP（設計・最小スケルトン）

**ステータス**: 作業ブランチ `work/r6-10-a-us-equities-cache-only-mvp` のみ。**`main` 未反映**。実装は **読み取り専用の最小関数**に限定。

---

## 19.1 目的

- **US equities / US ETF** レイヤーの土台として、**既存の sanitized JSON**（`schema_version`・`symbol`・`bars` 等）を **任意 `Path`** から読めるようにする。
- **cache-only**（外部 API へ接続しない・**live HTTP** なし）で **CI 再現可能な `pytest`** に載せる。
- 将来の **US signals**・**report**・**portfolio** 連携へ、**同じペイロード検証**を流用できるようにする。

## 19.2 非目的

- **live HTTP**・**API client**・**`.env` / API キー`**
- **production cache write**（`save_us_daily_bars_cache` の本番利用を増やすこと）
- 本格的スコアリング・**macro regime** 本実装・**portfolio allocation** 本実装

## 19.3 最小データモデル

既存 **`us_daily_bars_cache`** の on-disk 形を踏襲:

- ルートキーは `_ALLOWED_PAYLOAD_KEYS_AT_ROOT` と同一集合
- `bars` は **`bars_from_rows`** が解釈できる行辞書の配列

## 19.4 cache-only 読み込み

| 項目 | 方針 |
|------|------|
| 入力 | **`Path`** 上の JSON ファイル（**fixture** またはオペレータが配置したファイル） |
| 検証 | 既存 **`load_us_daily_bars_cache`** と同じ拒否ルール（余剰キー・禁止文字列・`schema_version`・symbol 正規化）を **`parse_us_daily_bars_payload`** に集約 |
| `expect_symbol` | 省略可。指定時はファイル内 `symbol` と **正規化後一致**が必要 |
| 欠損・不正 | **`None`** を返す（例外で落とさない読み取り経路） |

公開 API:

- **`parse_us_daily_bars_payload(data, expect_symbol=...)`** — 純粋検証
- **`load_us_daily_bars_json_file(path, expect_symbol=...)`** — ファイル I/O + 上記

## 19.5 テスト方針

- **`tests/fixtures/us_daily_bars/MSFT.json`** を正例に使用
- **wrong symbol**・**malformed JSON**・**空 `bars`** で `None` を確認
- **HTTP / cache write を呼ばない**（静的ファイルのみ）

## 19.6 将来拡張

- CLI / daily report への配線は **別タスク**（本 MVP では触れない）
- **Stooq** 等の ingest は **ゲート付き別ワークフロー**（既存設計ドキュメント参照）
