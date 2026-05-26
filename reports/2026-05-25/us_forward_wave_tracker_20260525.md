# US forward wave tracker（read-only）

Normal-mode `matched` toward P3 usable (threshold 10). Observation only.

| Wave | Gated | log lines | matched | backtest (exploratory) | insuf_share |
|---:|---|---:|---:|---:|---:|
| 10 | W/X | 254 | 3 | — | — |
| 11 | Y/Z | 274 | 3 | — | — |
| 12 | AA/AB | 294 | 3 | 256 | — |
| 13 | AC/AD | 314 | 3 | 256 | — |
| 14 | AE/AF | 334 | 3 | 272 | — |
| 15 | AG/AH | 354 | 3 | 288 | 93.4% |
| 16 | AI/AJ | 374 | **3** | **304** | **93.8%** |

**Note**: matched (normal) flat since wave6; backtest rises with log depth — not a milestone.

CLI: `validate forward-p3-status --format markdown`
