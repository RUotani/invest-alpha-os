"""Cache-only market regime v0 for context pack."""

from __future__ import annotations

from dataclasses import dataclass

from invis_alpha_os.reports.weekly_candidate_brief_quant_metrics import compute_candidate_quant_metrics

_US_PROXY = ("SPY", "QQQ")
_JP_PROXY = ("TOPIX", "1306", "1321", "^N225")


@dataclass(frozen=True)
class RegimeProxySnapshot:
    ticker: str
    market: str
    available: bool
    ret20: float | None
    ret60: float | None
    dist75: float | None
    dist200: float | None
    freshness_classification: str | None
    freshness_reason: str | None


def _snapshot_for_proxy(*, report_date: str, ticker: str, market: str) -> RegimeProxySnapshot:
    qm = compute_candidate_quant_metrics(symbol=ticker, market=market, report_date=report_date)
    available = qm.latest_close is not None
    return RegimeProxySnapshot(
        ticker=ticker,
        market=market,
        available=available,
        ret20=qm.ret_20d_pct,
        ret60=qm.ret_60d_pct,
        dist75=qm.dist_ma_75_pct,
        dist200=qm.dist_ma_200_pct,
        freshness_classification=qm.freshness_classification,
        freshness_reason=qm.freshness_reason,
    )


def _choose_first_available(report_date: str, proxies: tuple[str, ...], market: str) -> RegimeProxySnapshot | None:
    for ticker in proxies:
        snap = _snapshot_for_proxy(report_date=report_date, ticker=ticker, market=market)
        if snap.available:
            return snap
    return None


def _is_risk_on(s: RegimeProxySnapshot) -> bool:
    return bool(
        (s.ret20 is not None and s.ret20 > 0)
        and (s.ret60 is not None and s.ret60 > 0)
        and (s.dist75 is not None and s.dist75 > 0)
        and (s.dist200 is not None and s.dist200 > 0)
    )


def _is_risk_off(s: RegimeProxySnapshot) -> bool:
    return bool(
        (s.ret20 is not None and s.ret20 < 0)
        and (s.ret60 is not None and s.ret60 < 0)
        and (s.dist75 is not None and s.dist75 < 0)
        and (s.dist200 is not None and s.dist200 < 0)
    )


def build_market_regime_v0(*, report_date: str) -> dict[str, object]:
    spy = _snapshot_for_proxy(report_date=report_date, ticker="SPY", market="US")
    qqq = _snapshot_for_proxy(report_date=report_date, ticker="QQQ", market="US")
    topix = _choose_first_available(report_date, _JP_PROXY, "JP")
    nikkei = _snapshot_for_proxy(report_date=report_date, ticker="1321", market="JP")
    proxies = [x for x in (spy, qqq, topix, nikkei) if x is not None]
    available = [x for x in proxies if x.available]
    if len(available) < 2:
        label = "data_insufficient"
        note = "主要指数キャッシュが不足しておりレジーム判定不可"
    else:
        on = sum(1 for x in available if _is_risk_on(x))
        off = sum(1 for x in available if _is_risk_off(x))
        if on >= 2 and off == 0:
            label = "risk_on"
            note = "主要指数の中期モメンタムが上向き"
        elif off >= 2 and on == 0:
            label = "risk_off"
            note = "主要指数の中期モメンタムが下向き"
        else:
            label = "neutral"
            note = "指数間で方向感が混在"
    return {
        "label": label,
        "notes": [note],
        "proxies": [
            {
                "ticker": x.ticker,
                "market": x.market,
                "available": x.available,
                "ret20": x.ret20,
                "ret60": x.ret60,
                "dist_ma75_pct": x.dist75,
                "dist_ma200_pct": x.dist200,
                "freshness_classification": x.freshness_classification,
                "freshness_reason": x.freshness_reason,
            }
            for x in proxies
        ],
    }
