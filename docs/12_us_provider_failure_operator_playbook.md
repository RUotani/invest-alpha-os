# US provider / Stooq preview — failure matrix & operator playbook (Main R4.4–R5)

## 1. Purpose

This playbook is for **operators** using **`debug us-provider-live-preview`** (shape digest), **`debug us-provider-cache-preview`** (strict parse + optional single-symbol cache write), and **`debug us-provider-cache-preview-batch`** (multi-symbol **aggregated preview**, Main R5). It matches **in-repo implementation** as of **Main R4.3** per-symbol payloads plus **Main R5** batch envelope — **not** a wish list.

**Observation only** — no trading advice, no automated refresh, **no unattended** multi-symbol HTTP.

**Canonical reference:** **`stooq_live_preview_shape_digest`** / **`stooq_live_preview_sanitized_bars`** in **`us_provider_live_preview.py`**; batch envelope **`run_stooq_cache_preview_batch`** in **`us_provider_cache_preview_batch.py`**. If code and this doc disagree, **trust the code** and update this file.

---

## 2. Safe vs forbidden actions

### Allowed

- Read **`status`**, **`reason`**, and **`response_diagnostics`** (including **`body_kind`**, capped **`header_columns_sanitized`**, **`delimiter_guess`**, **`required_columns_missing`**, counts only).
- Read **`cache_target`** / planned output **path strings** from successful previews (no secrets there).
- Adjust **symbol normalization** and **Stooq wire slug** (e.g. `*.us`, class-B dots) using docs and `config/us_watchlist.yaml` — **no raw vendor bodies**.
- Add **tests/fixtures** using **hand-authored minimal safe samples** (no real API keys, no pasted live vendor dumps).

### Forbidden

- Saving **raw vendor HTTP bodies**, **raw CSV**, or full error pages to **`outputs/`**, **git**, **tickets**, or **chat logs**.
- Putting **API keys** in **stdout**, **stderr**, **committed docs**, **tests**, or **CI logs** — use **process env** / local **`.env`** only (`.env` is **not** committed).
- Running **live HTTP** from **automated tests** or **CI** (mock only).
- **Cache write** without **`CONFIRM_US_CACHE_WRITE=YES`** and explicit operator intent.
- **Unattended multi-symbol** live fetch or **scheduled bulk** refresh (post‑R5 design work unless explicitly gated elsewhere).

---

## 3. Failure matrix (Stooq preview commands)

**Legend**

- **body_kind:** `response_diagnostics.body_kind` when present; **—** if payload has no `response_diagnostics` (or not applicable).
- **Cache write allowed?:** whether it is **ever** correct to proceed to **sanitized** cache write **for this outcome**. Does not bypass gates.
- **Raw vendor body / CSV:** **Never** store, commit, paste into tickets/chat, or attach to CI/AI reviews. Operators must rely on **`status` / `reason` / `response_diagnostics`** only inside the repo toolchain. (**No exception** rows in the matrix.)

| status | reason (as emitted) | body_kind (typical) | Likely cause | Operator action | Cache write allowed? | Raw vendor body / CSV | Next milestone relevance |
|--------|---------------------|---------------------|--------------|-----------------|----------------------|-------------------------|--------------------------|
| `dry_run` | — | — | Preview invoked without `--live`. | Expected. Set `CONFIRM_US_LIVE_HTTP=YES` and `--live` only for intentional gated smoke. | No | Never | Baseline before any HTTP. |
| `live_preview_ok` | — | — | HTTP 200 + parseable CSV shape (**Main R3** path). | Symbol + wire slug look acceptable for **manual** smoke; still **prototype** tier. | No (shape path has no cache write) | Never | Single-symbol confidence only. |
| `preview_ok` | — | — | HTTP 200 + strict parse succeeded; **cache write flag off**. | Inspect row span; optionally retry with **`--write-cache`** + **`CONFIRM_US_CACHE_WRITE=YES`** if persistence intended. | **Only** after deliberate gate + `--write-cache` | Never | R5: replicate per-symbol “OK” rollup. |
| `success` | — | — | Parse OK + sanitized cache written. | **Human operator, local workspace only:** verify **sanitized JSON** exists at the indicated path (**do not** commit `outputs/market_data` / raw vendor material). | Yes (completed under gates) | Never | R5: per-symbol success aggregation. |
| `validation_error` | `live_http_not_confirmed` | — | `CONFIRM_US_LIVE_HTTP` not `YES`. | **Normal refusal.** No HTTP performed. | No | Never | Gate discipline for multi-symbol later. |
| `validation_error` | `cache_write_not_confirmed` | — | `--write-cache` without `CONFIRM_US_CACHE_WRITE=YES`. | **Normal refusal.** No cache write. | No | Never | Same gate pattern for R5 bulk guardrails. |
| `validation_error` | `provider_api_key_required` | `api_key_required` | HTTP 200 but vendor indicates API key / registration prose. | Set **`STOOQ_APIKEY`** in **env only**; **never** echo in docs/PR; retry **one** gated GET; don’t save raw body. | No until vendor returns parseable CSV | Never | R5: surface per-symbol “key required” in summary. |
| `validation_error` | `invalid_symbol` | — | Symbol failed **normalization**. | Fix ticker / watchlist input; no provider call in some paths. | No | Never | R5: invalid symbols excluded from batch. |
| `validation_error` | `preview_plan_failed` | — | `build_stooq_daily_preview` failed (config / internal). | Check `config/us_market_data.yaml` and preview builder; no HTTP in this path. | No | Never | R5: batch planner must fail fast on config. |
| `validation_error` | `missing_preview_url` | — | Transport URL could not be built from plan. | Check preview plan / base URL in config. | No | Never | Same. |
| `validation_error` | `unsupported_provider` | — | CLI **`--provider`** not `stooq_preview` (**Main R4** cache / live-preview commands). | Use **`stooq_preview`** as documented. | No | Never | R5: provider allow-list. |
| `parse_error` | `stooq_payload_html_like` | `html_like` | HTML / interstitial instead of CSV. | Treat as **vendor block or format change**; rely on **`reason` + `body_kind`** only. | No | Never | R5: count as **non-CSV** class. |
| `parse_error` | `stooq_vendor_no_data` | `no_data_like` | Terse **no data** / symbol messages. | Re-check **`.us` slug**, listing type (ETF/ADR), class shares; **log finding in prose**, not raw response. | No | Never | R5: per-symbol “no data” bucket. |
| `parse_error` | `empty_csv` | `empty` | Whitespace-only or empty tabular attempt. | Confirm network path; retry later; don’t persist empty vendor bodies. | No | Never | R5: empty bucket. |
| `parse_error` | `stooq_csv_delimiter_drift` | `delimiter_drift` | Header vs data **delimiter mismatch** (heuristic). | Suspect **vendor format change**; use **fixture + tests** to lock behavior; **no raw CSV** in repo. | No | Never | R5: delimiter issues as first-class summary. |
| `parse_error` | `stooq_csv_missing_required_columns` | often `csv_like` / partial | Wrong header schema. | Fix mapping or accept provider unsupported for strict schema. | No | Never | R5: schema mismatch tally. |
| `parse_error` | `stooq_csv_parse_failed` | varies | Strict parser rejected rows (numeric / date / duplicate dates / etc.). | Inspect **diagnostics only**; if reproducible, add **minimal synthetic fixture**. | No | Never | R5: parse failure counts per symbol. |
| `parse_error` | `stooq_csv_no_rows` | often `csv_like` or `empty` | No data rows after header. | Similar to vendor empty / truncation; mapping check. | No | Never | R5: row-count zero bucket. |
| `parse_error` | `csv_parse_failed` | often present | **`csv.reader`** could not ingest text (shape digest path). | Malformed quoting / line breaks; use diagnostics; don’t hoard raw blob. | No | Never | R5: pre-parse failure bucket. |
| `parse_error` | `csv_decode_failed` | — | Bytes are not valid UTF-8 strict decode. | Transient encoding / binary error page; retry not guaranteed. | No | Never | Rare; keep out of aggregation until classified. |
| `parse_error` | `cache_persist_refused` | — | `save_us_daily_bars_cache` raised **`ValueError`** (**sanitized writer** refusal). | Check path policy / manifest rules; fix operator inputs. | **Blocked** — fix inputs | Never | R5: writer guard parity across symbols. |
| `http_error` | `network_or_timeout` | — | **`URLError`**, **`TimeoutError`**, **`OSError`** from transport. | Network / TLS / transient; bounded retry operator-only. | No | Never | R5: transport failure bucket (**no** unattended retry loop). |
| `http_error` | `http_status_<code>` | — | **`HTTPError`** from server (non-2xx handled here). | Check code (403/404/5xx); don’t scrape error **body** into repo. | No | Never | R5: HTTP class per symbol. |
| `http_error` | `http_error` | — | HTTP error **without numeric code** (edge). | Same as generic HTTP failure class. | No | Never | Same. |

**CLI exit hints (approximate):** `validation_error` → exit **2**; `dry_run`, `live_preview_ok`, `preview_ok`, `success` → exit **0**; `parse_error` / `http_error` → exit **1**. See Typer handlers in `src/invis_alpha_os/cli/main.py` for edge cases (`unsupported_provider` returns JSON then exit **2**).

### Multi-symbol batch envelope (**`debug us-provider-cache-preview-batch`**, Main R5)

| Outer `status` | Typical batch `reason` | Operator notes |
|----------------|----------------------|----------------|
| `batch_preview_ok` | — | **`results[]`** carries one row per requested symbol (**invalid_symbol** tokens appear inline). **`summary`** buckets row **`status`** (**`transport_error`** counts **`http_error`** rows). **`write_cache_requested`** is **false** in payloads — batch **never** persists cache. CLI exit **0**. |
| `validation_error` | `unsupported_provider` | Wrong **`--provider`**. CLI exit **2**. |
| `validation_error` | `batch_cache_write_not_supported` | **`--write-cache`** is rejected — use **`debug us-provider-cache-preview`** with gates. CLI exit **2**. |
| `validation_error` | `empty_symbol_batch` | Provide **`--symbols`** and/or **`--from-watchlist`**. CLI exit **2**. |

Per-row **`cache_write_allowed`** (**preview_ok** + gated **`live_http_performed`**) signals **single-symbol follow-up write** (**`debug us-provider-cache-preview --write-cache`**) eligibility — **not** the batch path (**bulk cache writes intentionally unsupported**).

---

## 4. Operator playbooks by theme

### Gates (not errors)

- **`live_http_not_confirmed`**, **`cache_write_not_confirmed`**: deliberate **human gates**. No vendor call or no disk write occurred — **safe by design**.

### Multi-symbol aggregation (batch)

- **`make us-provider-cache-preview-batch-dry-run`** runs the batch CLI with **`--from-watchlist`**, **`--provider stooq_preview`**, and **`--limit 4`** only. **`debug us-provider-cache-preview-batch`** has **no** **`--quiet`** or **`--dry-run`** options — leaving off **`--live`** is what keeps previews in **`dry_run`** (**no HTTP**). **`--live`** still requires **`CONFIRM_US_LIVE_HTTP=YES`** and implies **human-invoked sequential GETs**.
- Inspect **`results[]`**, **`summary`**, **`operator_next_action`**, **`docs/11`** wire slug guidance (**no raw vendor bodies**) before diagnosing watchlist failures at scale — **bulk cache writes remain deliberately unsupported.**

### API key prose

- **`provider_api_key_required`**: configure **`STOOQ_APIKEY`** in environment; **never** paste into tickets or docs; **never** persist vendor HTML/CSV **raw**. After key is set, one gated retry is sufficient for **manual** smoke — not proof of entitlement for automation.

### Non-CSV payloads

- **`stooq_payload_html_like`**: vendor block, CDN interstitial, or **HTML error as 200**. Do **not** “debug by saving HTML.” Escalate to **alternate data path** (fixtures, manual file import) unless vendor contract improves.

### No data prose

- **`stooq_vendor_no_data`**: ticker / **`*.us`** / class-B mapping suspected before blaming “Stooq down.” Record **operator note** referencing **`reason`** and **`body_kind`**, **not** raw text.

### Delimiter drift

- **`stooq_csv_delimiter_drift`**: treat as **vendor format risk**. Prefer **minimal synthetic reproduction** inside **tests**, not dumping live responses.

### HTTP / transport

- **`network_or_timeout`**, **`http_status_*`**: infra or vendor outage; bounded human retry OK; **no** CI/live loops.

### Standard schema / numeric parse failures

- **`stooq_csv_missing_required_columns`**, **`stooq_csv_parse_failed`**, **`stooq_csv_no_rows`**, **`csv_parse_failed`**: fix **mapping** / **fixture** alignment; **`response_diagnostics`** is the only in-repo microscope.

---

## 5. R5 implementation notes (implemented)

**Delivered behaviors (operators):**

- **Multi-symbol aggregation** CLI: **`inv debug us-provider-cache-preview-batch`** merges **`--from-watchlist`** + **`--symbols`**, trims duplicates, honours **`limit`**, and prints JSON with **`batch_preview_ok`**, **`symbol_count`**, **`results[]`**, **`summary`**, **`observation_only=true`** (**no raw vendor payloads** embedded).
- **Makefile**: **`make us-provider-cache-preview-batch-dry-run`** passes **`--from-watchlist`**, **`--provider stooq_preview`**, and **`--limit 4`** (**no** **`--quiet`**, **no** **`--dry-run`** — CLI default is **`dry_run`** unless **`--live`** is supplied). **`safe-push`** intentionally **does not** depend on batch targets (**unit tests gate this invariant**).

**Safety rules remain unchanged:**

- **No unattended live HTTP**, **no default cache write**, **no bulk sanitized writer** (`--write-cache` at batch ⇒ **`batch_cache_write_not_supported`**), **never commit `outputs/market_data`**, **do not use `ALLOW_IMPORTANT=true`** to bypass workflow gates (unchanged policy).

**Documentation touchpoints:**
- Canonical module: **`src/invis_alpha_os/data/us_provider_cache_preview_batch.py`**.

**Explicit future work:**

- Automated watchlist ingestion at cron scale (**still out-of-scope until product owners green-light production gates).

---

## 6. Standard outcomes for aggregate planning

Treat these **`reason`** values as **first-class buckets** when comparing symbols (**batch `summary`** in Main R5 and later planning):

- **Gates:** `live_http_not_confirmed`, `cache_write_not_confirmed`
- **Key / entitlement:** `provider_api_key_required`
- **Vendor non-tabular:** `stooq_payload_html_like`, `stooq_vendor_no_data`, `empty_csv`
- **Format / schema:** `stooq_csv_delimiter_drift`, `stooq_csv_missing_required_columns`, `stooq_csv_parse_failed`, `stooq_csv_no_rows`, `csv_parse_failed`, `csv_decode_failed`
- **Transport:** `network_or_timeout`, `http_status_*`, `http_error`
- **Success path:** `live_preview_ok` (shape-only), `preview_ok` / `success` with strict parser

Anything **not reproducible via diagnostics + operator notes** should **not** become a KPI — **avoid raw-body forensics.**
