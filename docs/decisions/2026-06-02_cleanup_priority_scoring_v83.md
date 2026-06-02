# v83 Cleanup Priority Scoring Pack

Date: 2026-06-02

## 背景

v79 confirmed weekly candidate brief artifact generation, v80 recorded that the artifact was not sufficient as an
investment decision-support report, v81 improved the zero-candidate UX, and v85 added a portfolio-aware weekly action
checklist.

The next gap is that the weekly report still leans toward new-candidate discovery. Under the v78 redacted portfolio
context, the more important weekly question is often which existing risk bucket should be reviewed first.

## 目的

Add observation-only cleanup / monitoring priority scoring to the Weekly Candidate Brief.

The score helps rank review pressure across:

- individual-stock allocation
- high-beta exposure
- equity overlap / duplication risk
- data-blocked candidate groups

## 追加した機能

- `## 整理・監視優先度スコア` in the copy-ready Weekly Candidate Brief
- group-level priority rows when actual position-level holdings are not available
- score axis table for cash pressure, allocation excess, evidence gap, volatility risk, and duplication risk
- compact email text / HTML cleanup priority output
- action checklist links from high cleanup priority to weekly allowed / suppressed / next-check actions

## スコアリング軸

| Axis | Meaning |
|---|---|
| `cash_pressure` | Review pressure caused by cash at `508.2万円 / 11.7%`, below the 15% minimum guide |
| `allocation_excess` | Pressure from individual stocks `846.3万円 / 19.6%` and equity total `2,934.5万円 / 67.8%` |
| `evidence_gap` | Missing coverage, score, price, data freshness, or veto evidence |
| `volatility_risk` | High-beta / crypto-like / leveraged exposure pressure |
| `duplication_risk` | Overlap between INDEX exposure and individual-stock / theme exposure |

Score interpretation:

- `0`: 今週は対象外
- `1`: 低い監視
- `2`: 軽い確認
- `3`: 要確認
- `4`: 高優先で監視・整理検討
- `5`: 強い抑制・新規追加禁止寄り

## Safety Boundary

This milestone is source-only and observation-only.

Explicitly not approved:

- workflow changes or `.github/workflows` changes
- provider live HTTP or market-data live fetch
- cache write or cache directory creation
- actual refresh/import or manual actual import
- broker API access or broker login
- raw broker export parsing
- raw broker data persistence
- raw OHLCV/API persistence
- raw Excel direct parsing
- reports-private raw data write
- Git-tracked raw data write
- env/secret display
- dependency / pyproject / Makefile changes
- trading action or order placement
- automated buy/sell execution recommendation

## 売買推奨ではない理由

The score is group-level review pressure, not position-level execution guidance. It does not read broker exports, does
not access broker APIs, does not fetch live market data, and does not generate order instructions.

The report explicitly states:

> このスコアは売却指示ではなく、次に確認すべき整理・監視優先度です。

## 次の改善候補

1. v82 Target Allocation Gap Calculator
2. position-level cleanup scoring only after a human-redacted holdings snapshot is approved
3. scheduled weekly artifact review with v83/v85 output after the next Saturday JST run
