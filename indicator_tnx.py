"""
指标5：美债利率景气度（权重10%）
============================================================
标的：^TNX（10年期美国国债收益率）
逻辑：收益率越低 → 利好AI板块估值 → 景气度得分越高（反向映射）
计算方式：当前收益率绝对值映射到0-100
============================================================
"""

import yfinance as yf
import pandas as pd

TICKER = "^TNX"
WEIGHT = 0.10

# 映射表：收益率越低，得分越高（反向关系）
# (阈值, 得分) — 从上往下匹配，命中即停
MAPPING = [
    (2.5, 100),
    (3.2, 90),
    (3.8, 75),
    (4.5, 50),
    (5.5, 25),
    (float("inf"), 0),
]


def fetch_data() -> pd.Series:
    """拉取^TNX近2年日线，返回Close序列"""
    ticker = yf.Ticker(TICKER)
    hist = ticker.history(period="2y", auto_adjust=True)
    hist.sort_index(inplace=True)
    hist = hist[~hist.index.duplicated(keep="first")]
    series = hist["Close"].copy()
    series.name = TICKER
    return series


def map_score(yield_val: float) -> int:
    """根据当前收益率绝对值映射0-100得分"""
    for threshold, score in MAPPING:
        if yield_val < threshold:
            return score
    return 0


def run():
    print("指标5：美债利率景气度（权重10%）")
    print("=" * 60)

    series = fetch_data()
    latest_date = series.index[-1]
    current_yield = float(series.iloc[-1])

    print(f"数据范围：{series.index[0].strftime('%Y-%m-%d')} → {latest_date.strftime('%Y-%m-%d')}")
    print(f"实际数据条数：{len(series)} 个交易日")
    print()

    score = map_score(current_yield)

    print(f"当前日期: {latest_date.strftime('%Y-%m-%d')}")
    print(f"10年期美债收益率: {current_yield:.2f}%")
    print()

    # 打印匹配的区间
    for threshold, s in MAPPING:
        if current_yield < threshold:
            if threshold == float("inf"):
                print(f"映射区间: [5.5, inf)")
            else:
                prev = [t for t, _ in MAPPING if t < threshold]
                lo = prev[-1] if prev else 0
                print(f"映射区间: [{lo}, {threshold})")
            break

    print(f"→ 景气度得分: {score} / 100")


if __name__ == "__main__":
    run()
