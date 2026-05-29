# US OHLCV provider selection operating model

日付: 2026-05-30
ステータス: approved-by-task
関連: v36 Provider Automation Core, v44 Execution Approval Request, `RULES.md` §1/§5

## 結論

- US OHLCV provider はまだ selected ではない。
- v46 は source-only の selection matrix と pilot design を作るだけで、live provider test は実行しない。
- Broad US stock recommendation は、coverage、adjustment、corporate actions、terms/cache suitability、rate limits を検証するまで production data source として扱わない。

## 評価軸

- US stock / ETF / ADR / delisted coverage
- historical depth
- daily OHLCV availability
- adjusted close / adjusted OHLC support
- split / dividend / corporate action support
- bulk suitability and rate-limit risk
- API stability and Python implementation effort
- terms/cache suitability review
- cost tier and fit for pilot / production / fallback

## Pilot design

- Pilot universe は `AAPL, MSFT, NVDA, AMD, AVGO, TSLA, GOOGL, AMZN, META, JPM, XOM, UNH, SPY, QQQ` とする。
- First pilot candidate は `Tiingo`、production candidate は `Polygon.io`、free fallback は `Stooq` とする。
- この順位は source-only planning に基づく暫定順位で、live evidence ではない。

## Hard gates

- `public OHLCV source live fetchを実行してよい`
- `cache writeを実行してよい`
- `actual refresh/importを実行してよい`

v46 では上記を実行しない。最初の live pilot は public OHLCV source live fetch のみを別承認し、cache write / actual import は明示的に除外する。

## 反証

- Pricing、terms、rate limits は変わるため、source-only matrix だけで provider を確定すると危険。
- Free provider は便利だが、adjustment policy と cache terms が曖昧なら production recommendation には使わない。
- Paid provider でも plan tier によって coverage / rate limits / delisted support が変わる可能性がある。

## 次アクション

- v44 approval request を使い、`public_ohlcv` scenario の small pilot を別承認タスクとして作る。
- 実行前に current pricing / terms / cache suitability を確認する。
- cache write と actual import は pilot fetch の結果レビュー後まで承認しない。
