# Evidence Manifest — p10_amd_refresh

**generated_at**: 2026-05-24  
**task_id**: p10_amd_refresh  
**secret-free**: yes（本文に API key / token なし）

---

| 項目 | 値 |
| --- | --- |
| evidence path | `outputs/evidence/p10_tier1_amd_refresh_20260524.md` |
| size_bytes | 644 |
| sha256 | `49c28b293cc31f5c161023daca487051d1a8645fa7d242a6c00392d61e6223cf` |
| command | `CONFIRM_US_LIVE_HTTP=YES CONFIRM_US_CACHE_WRITE=YES debug us-provider-cache-preview --symbol AMD --provider stooq_preview --live --write-cache` |
| result | `validation_error` / `provider_api_key_required` |
| cache_write_performed | false |
| human_approval | yes (AskQuestion p10_refresh) |
| blocker | `STOOQ_APIKEY` 未設定 |

## Summary

P10 tier-1 AMD refresh は live HTTP 到達後 Stooq API key 要求で停止。cache 未書込。再試行は env preflight 後（docs/162 · longrun standard §11）。
