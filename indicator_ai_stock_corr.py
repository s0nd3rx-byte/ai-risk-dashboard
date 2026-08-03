"""
指标4：AI股间价格相关性（权重20%）
================================================================
逻辑：10只AI标的 → 每日涨跌幅 → 60日滚动两两Pearson相关系数 → 取均值
      相关性越高 → AI内部同质化越严重 → 踩踏风险越大 → 得分越高
映射：基于历史分位数（当前均值相关性在过去两年历史中的位置）
      7档统一得分 0/25/40/60/75/90/100
================================================================
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from itertools import combinations


# ================================================================
# 配置
# ================================================================
AI_STOCKS = ["NVDA", "AMD", "MU", "MRVL", "MSFT", "GOOGL", "AMZN", "META", "PLTR", "AVGO"]
CORR_WINDOW = 60          # 60日滚动窗口
LOOKBACK_YEARS = 2        # 取近2年数据
WEIGHT = 0.20             # 权重20%

# 7档映射：基于历史分位数
BINS_PCT = [0, 20, 40, 60, 80, 90, 95, 101]
SCORES = [25, 25, 40, 60, 75, 90, 100]
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
    """拉取10只AI标的近2年日线"""
    end = datetime.today()
    start = end - timedelta(days=365 * LOOKBACK_YEARS + 60)
    print(f"数据范围：{start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}")
    print(f"AI标的 ({len(AI_STOCKS)}只)：{', '.join(AI_STOCKS)}")

    raw = yf.download(
        AI_STOCKS,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        auto_adjust=True,
        progress=False,
    )

    # 提取Close
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
    else:
        close = pd.DataFrame({s: raw["Close"] for s in AI_STOCKS})

    close = close.dropna()
    print(f"对齐后数据条数：{len(close)} 个交易日")
    return close


def compute_avg_pairwise_corr(prices: pd.DataFrame) -> tuple:
    """计算60日两两相关系数均值，返回当前值和完整序列"""
    returns = prices.pct_change().dropna()

    # 计算所有两两组合的60日滚动相关系数
    n = len(AI_STOCKS)
    n_pairs = n * (n - 1) // 2  # C(10,2) = 45对
    print(f"\n两两配对总数: {n_pairs} 对")

    # 预分配矩阵存储每对的滚动相关系数
    pair_corrs = {}
    for s1, s2 in combinations(AI_STOCKS, 2):
        rolling_corr = returns[s1].rolling(CORR_WINDOW).corr(returns[s2])
        pair_corrs[(s1, s2)] = rolling_corr

    # 按日期取所有对的均值
    all_pairs_df = pd.DataFrame(pair_corrs)
    avg_corr = all_pairs_df.mean(axis=1).dropna()

    current_avg = avg_corr.iloc[-1]
    corr_min = avg_corr.min()
    corr_max = avg_corr.max()
    date_current = avg_corr.index[-1].strftime("%Y-%m-%d")

    print(f"最新日期: {date_current}")
    print(f"60日平均相关性范围: {corr_min:.3f} ~ {corr_max:.3f}")
    print(f"当前平均相关性: {current_avg:.3f}")

    # 列出当前各对的相关性（Top 5 + Bottom 5）
    current_pair_vals = {pair: all_pairs_df[pair].iloc[-1] for pair in pair_corrs}
    sorted_pairs = sorted(current_pair_vals.items(), key=lambda x: x[1], reverse=True)
    print(f"\n最高5对:")
    for (s1, s2), val in sorted_pairs[:5]:
        print(f"  {s1}-{s2}: {val:.3f}")
    print(f"最低5对:")
    for (s1, s2), val in sorted_pairs[-5:]:
        print(f"  {s1}-{s2}: {val:.3f}")

    return current_avg, avg_corr


def map_score_by_percentile(current_corr: float, rolling_corr: pd.Series) -> tuple:
    """基于历史分位数映射到7档得分"""
    hist_min = rolling_corr.min()
    hist_max = rolling_corr.max()

    if hist_max - hist_min < 0.001:
        percentile = 50.0
    else:
        percentile = (current_corr - hist_min) / (hist_max - hist_min) * 100

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
    """对整个均值相关性序列逐点映射得分（基于全历史 min/max）"""
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
    print("指标4：AI股间价格相关性（权重20%）")
    print("=" * 60)
    print(f"窗口：{CORR_WINDOW}个交易日")
    print()

    prices = fetch_data()
    current_corr, rolling_corr = compute_avg_pairwise_corr(prices)
    score, label, pct = map_score_by_percentile(current_corr, rolling_corr)

    # ── 历史序列 ──
    all_scores = map_full_history(rolling_corr)
    history = all_scores[-30:]
    prev_score = all_scores[-6] if len(all_scores) >= 6 else score

    trend = "up" if score > prev_score else ("down" if score < prev_score else "flat")
    raw_label = f"均值 {current_corr:.3f} (分位 {pct:.0f}%)"

    weighted = score * WEIGHT
    print(f"\n映射区间: {label}")
    print(f"→ 风险预警得分: {score} / 100")
    print(f"  (权重 {int(WEIGHT*100)}%，加权 {weighted:.1f})")
    return {"score": score, "prev_score": prev_score, "history": history,
            "raw_value": raw_label, "trend": trend}


if __name__ == "__main__":
    run()
