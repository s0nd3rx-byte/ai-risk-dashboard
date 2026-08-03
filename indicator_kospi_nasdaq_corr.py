"""
指标3：Kospi-Nasdaq 60日滚动相关性（权重20%）
================================================================
逻辑：Kospi(^KS11) 和 Nasdaq(^IXIC) 每日涨跌幅 → 60日滚动Pearson相关系数
      相关性越高 → 韩美联动越紧 → 传染风险越大 → 得分越高
映射：基于历史分位数（当前相关性在过去两年历史中的位置）
      7档统一得分 0/25/40/60/75/90/100
================================================================
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


# ================================================================
# 配置
# ================================================================
KOSPI = "^KS11"
NASDAQ = "^IXIC"
CORR_WINDOW = 60          # 60日滚动窗口
LOOKBACK_YEARS = 2        # 取近2年数据
WEIGHT = 0.20             # 权重20%

# 7档映射：基于历史分位数（百分位越高 → 得分越高 → 越危险）
BINS_PCT = [0, 20, 40, 60, 80, 90, 95, 101]   # 百分位区间
SCORES = [0, 25, 40, 60, 75, 90, 100]
LABELS_PCT = [
    "< 20% 分位 (历史低位)",
    "20~40% 分位 (偏低)",
    "40~60% 分位 (中等偏低)",
    "60~80% 分位 (中等偏高)",
    "80~90% 分位 (高位)",
    "90~95% 分位 (极高位)",
    "> 95% 分位 (历史极值附近)",
]


def fetch_data() -> pd.DataFrame:
    """拉取 Kospi 和 Nasdaq 近2年日线"""
    end = datetime.today()
    start = end - timedelta(days=365 * LOOKBACK_YEARS + 60)
    print(f"数据范围：{start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}")

    nasdaq_used = NASDAQ
    raw = yf.download(
        [KOSPI, nasdaq_used],
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        auto_adjust=True, progress=False,
    )

    # 如果 ^IXIC 失败，切 ^NDX 重试
    if raw.empty or (isinstance(raw.columns, pd.MultiIndex) and nasdaq_used not in raw["Close"].columns):
        nasdaq_used = "^NDX"
        print(f"  [WARN] ^IXIC 不可用，切换备用: {nasdaq_used}")
        raw = yf.download(
            [KOSPI, nasdaq_used],
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            auto_adjust=True, progress=False,
        )

    print(f"标的：{KOSPI} vs {nasdaq_used}")

    if isinstance(raw.columns, pd.MultiIndex):
        close = pd.DataFrame({
            "kospi": raw["Close"][KOSPI],
            "nasdaq": raw["Close"][nasdaq_used],
        })
    else:
        close = pd.DataFrame({
            "kospi": raw["Close"],
            "nasdaq": raw["Close"],
        })

    close = close.dropna()
    if len(close) == 0:
        raise RuntimeError(f"无法获取 {KOSPI} 和 {nasdaq_used} 的数据，请检查网络/VPN")

    print(f"实际数据条数：{len(close)} 个交易日")
    return close

    close = close.dropna()
    print(f"实际数据条数：{len(close)} 个交易日")
    return close


def compute_correlation(prices: pd.DataFrame) -> tuple:
    """计算60日滚动Pearson相关系数，返回当前值和完整序列"""
    returns = prices.pct_change().dropna()
    rolling_corr = returns["kospi"].rolling(CORR_WINDOW).corr(returns["nasdaq"])
    rolling_corr = rolling_corr.dropna()

    current_corr = rolling_corr.iloc[-1]
    corr_min = rolling_corr.min()
    corr_max = rolling_corr.max()
    date_current = rolling_corr.index[-1].strftime("%Y-%m-%d")

    print(f"\n最新日期: {date_current}")
    print(f"60日滚动相关性范围: {corr_min:.3f} ~ {corr_max:.3f}")
    print(f"当前相关性: {current_corr:.3f}")

    return current_corr, rolling_corr


def map_score_by_percentile(current_corr: float, rolling_corr: pd.Series) -> tuple:
    """基于历史分位数映射到7档得分"""
    hist_min = rolling_corr.min()
    hist_max = rolling_corr.max()

    # 当前值在历史中的百分位
    if hist_max - hist_min < 0.001:
        percentile = 50.0  # 极窄区间，默认中位
    else:
        percentile = (current_corr - hist_min) / (hist_max - hist_min) * 100

    # 落到对应档位
    for i in range(len(BINS_PCT) - 1):
        if BINS_PCT[i] <= percentile < BINS_PCT[i + 1]:
            score = SCORES[i]
            label = LABELS_PCT[i]
            break
    else:
        score = SCORES[-1]
        label = LABELS_PCT[-1]

    print(f"历史分位数: {percentile:.1f}%  (历史最低 {hist_min:.3f}, 历史最高 {hist_max:.3f})")

    return score, label, percentile


def map_full_history(rolling_corr):
    """对整个相关性序列逐点映射得分（基于全历史 min/max）"""
    hist_min = rolling_corr.min()
    hist_max = rolling_corr.max()
    if hist_max - hist_min < 0.001:
        return [50] * len(rolling_corr)
    scores = []
    for v in rolling_corr.values:
        pct = (v - hist_min) / (hist_max - hist_min) * 100
        for i in range(len(BINS_PCT) - 1):
            if BINS_PCT[i] <= pct < BINS_PCT[i + 1]:
                scores.append(SCORES[i])
                break
        else:
            scores.append(SCORES[-1])
    return scores


def run():
    print("=" * 60)
    print("指标3：Kospi-Nasdaq 60日滚动相关性（权重20%）")
    print("=" * 60)
    print(f"标的：{KOSPI} vs {NASDAQ}")
    print(f"窗口：{CORR_WINDOW}个交易日")
    print()

    prices = fetch_data()
    current_corr, rolling_corr = compute_correlation(prices)
    score, label, pct = map_score_by_percentile(current_corr, rolling_corr)

    # ── 历史序列 ──
    all_scores = map_full_history(rolling_corr)
    history = all_scores[-30:]
    prev_score = all_scores[-6] if len(all_scores) >= 6 else score

    trend = "up" if score > prev_score else ("down" if score < prev_score else "flat")
    raw_label = f"相关性 {current_corr:.3f} (分位 {pct:.0f}%)"

    weighted = score * WEIGHT
    print(f"\n映射区间: {label}")
    print(f"→ 风险预警得分: {score} / 100")
    print(f"  (权重 {int(WEIGHT*100)}%，加权 {weighted:.1f})")
    return {"score": score, "prev_score": prev_score, "history": history,
            "raw_value": raw_label, "trend": trend}


if __name__ == "__main__":
    run()
