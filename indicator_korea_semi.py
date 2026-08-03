"""
============================================================
指标3：韩国半导体出口景气度（权重20%）
数据源：yfinance — SK海力士(000930.KS) ×70% + 三星电子(005930.KS) ×30%
逻辑：韩股半导体代表股价 YoY 涨跌幅 → 映射 0-100
使用 Adj Close（复权价）
============================================================
"""
import yfinance as yf
import pandas as pd
import numpy as np

TICKERS = {"000660.KS": "SK海力士", "005930.KS": "三星电子"}
WEIGHTS = {"000660.KS": 0.70, "005930.KS": 0.30}
LOOKBACK_YEARS = 2
TRADING_DAYS = 252

MAPPING = [
    (float("-inf"), -30,   0),
    (-30, -15,   25),
    (-15,   0,   40),
    (  0,  15,   60),
    ( 15,  40,   70),
    ( 40,  80,   78),
    ( 80, 150,   85),
    (150, 300,   93),
    (300, float("inf"), 100),
]


def fetch_data():
    end = pd.Timestamp.today().normalize()
    start = end - pd.DateOffset(years=LOOKBACK_YEARS)
    print(f"数据范围：{start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}")

    close_prices = {}
    for ticker, name in TICKERS.items():
        # 用 Ticker.history() + auto_adjust=True，确认拿到复权价
        t = yf.Ticker(ticker)
        raw = t.history(start=start, end=end, auto_adjust=True)
        if raw.empty:
            raise RuntimeError(f"无法拉取 {name} ({ticker}) 数据")

        close = raw["Close"].dropna()
        # 去掉重复索引
        close = close[~close.index.duplicated(keep="first")]

        print(f"\n[DIAG] {name} — 共{len(close)}条，最早{close.index[0].strftime('%Y-%m-%d')} @ {close.iloc[0]:.0f}，最新{close.index[-1].strftime('%Y-%m-%d')} @ {close.iloc[-1]:.0f}")

        close_prices[ticker] = close

    df = pd.DataFrame(close_prices).dropna()
    print(f"\n对齐后数据条数：{len(df)} 个交易日")
    return df


def calc_yoy_growth(df):
    latest = df.index[-1]
    target = latest - pd.DateOffset(weeks=52)
    mask = df.index <= target
    year_ago = df.index[mask][-1] if mask.any() else df.index[0]

    print(f"\n当前日期: {latest.strftime('%Y-%m-%d')}")
    print(f"52周前:   {year_ago.strftime('%Y-%m-%d')}")

    weighted_growth = 0.0
    for ticker, name in TICKERS.items():
        p_now = df[ticker].loc[latest]
        p_then = df[ticker].loc[year_ago]
        growth = (p_now / p_then - 1) * 100
        weighted_growth += growth * WEIGHTS[ticker]
        print(f"  {name}: {p_then:.0f} → {p_now:.0f}    YoY {growth:+.1f}%  (权重{WEIGHTS[ticker]:.0%})")

    print(f"\n加权YoY涨跌幅: {weighted_growth:+.1f}%")
    return weighted_growth


def map_score(growth):
    for low, high, score in MAPPING:
        if low <= growth < high:
            return score, f"[{low}, {high})"
    return 100, "100+"


def run():
    print("=" * 60)
    print("指标3：韩国半导体出口景气度（权重20%）")
    print("=" * 60)
    print(f"成分：SK海力士(70%), 三星电子(30%)")
    df = fetch_data()
    growth = calc_yoy_growth(df)
    score, interval = map_score(growth)
    print(f"映射区间: {interval}")
    print(f"→ 景气度得分: {score} / 100")


if __name__ == "__main__":
    run()
