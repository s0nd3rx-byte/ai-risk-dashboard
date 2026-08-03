"""
============================================================
指标4：费城半导体指数景气度
数据源：yfinance 拉取 ^SOX
计算：^SOX 同比涨幅 → 分段映射 0-100
权重：20%
============================================================
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# ============================================================
# 配置
# ============================================================
TICKER = "^SOX"
YEARS_BACK = 2  # 拉近2年数据（YoY需要1年+缓冲）

# 映射表：(下限, 上限, 得分)
# 指数波动天然小于个股，阈值整体压低
MAP = [
    (-float("inf"), -30,   0),
    (-30,          -15,   25),
    (-15,           0,    40),
    (0,            15,    60),
    (15,           30,    75),
    (30,           60,    85),
    (60,           100,   93),
    (100,     float("inf"), 100),
]

WEIGHT = 0.20


def fetch_data():
    end = datetime.now()
    start = end - timedelta(days=YEARS_BACK * 365 + 30)
    print(f"数据范围：{start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}")

    ticker = yf.Ticker(TICKER)
    hist = ticker.history(start=start, end=end, auto_adjust=True)

    # 去重索引
    hist = hist[~hist.index.duplicated(keep="first")]

    if hist.empty:
        raise RuntimeError(f"{TICKER} 无数据返回")

    prices = hist["Close"]
    print(f"实际数据条数：{len(prices)} 个交易日")
    return prices


def compute_yoy(prices):
    latest_idx = prices.index[-1]
    latest_price = prices.iloc[-1]

    # 找52周前最近交易日
    target = latest_idx - pd.DateOffset(years=1)
    idx_before = prices.index[prices.index <= target]
    if idx_before.empty:
        raise RuntimeError("过去一年没有足够交易数据")

    year_ago_idx = idx_before[-1]
    year_ago_price = prices.loc[year_ago_idx]

    yoy_pct = (latest_price / year_ago_price - 1) * 100

    print(f"\n当前日期: {latest_idx.strftime('%Y-%m-%d')}")
    print(f"52周前:   {year_ago_idx.strftime('%Y-%m-%d')}")
    print(f"  SOX: {year_ago_price:.2f} → {latest_price:.2f}    YoY {yoy_pct:+.1f}%")

    return yoy_pct


def map_score(yoy_pct):
    for low, high, score in MAP:
        if low <= yoy_pct < high:
            return score, f"[{low}, {high})"
    # 理论上走不到这里（最后一个区间上界是inf）
    return MAP[-1][2], f"[{MAP[-1][0]}, inf)"


def run():
    print("=" * 60)
    print("指标4：费城半导体指数景气度（权重20%）")
    print("=" * 60)

    prices = fetch_data()
    yoy_pct = compute_yoy(prices)
    score, interval = map_score(yoy_pct)

    print(f"\n映射区间: {interval}")
    print(f"→ 景气度得分: {score} / 100")


if __name__ == "__main__":
    run()
