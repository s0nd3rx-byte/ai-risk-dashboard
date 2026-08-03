"""
============================================================
指标2：HBM代理回撤（权重25%）
- SK海力士+三星合成HBM代理指数
- 从滚动252日高点回撤
- 回撤越大 → 得分越高 → 越危险
- 7档统一得分: 0/25/40/60/75/90/100
============================================================
"""
import yfinance as yf
import pandas as pd
import numpy as np

# ============================================================
# 配置
# ============================================================
SK_HYNIX = "000660.KS"
SAMSUNG = "005930.KS"
WEIGHT_SK = 0.70
WEIGHT_SAMSUNG = 0.30
LOOKBACK_DAYS = 252  # 滚动窗口

# --- 回撤映射（回撤越大=越危险=分越高）---
BINS = [-np.inf, 2, 5, 10, 20, 35, 50, np.inf]
SCORES = [0, 25, 40, 60, 75, 90, 100]
BIN_LABELS = [
    "<2% (新高附近)",
    "2~5% (接近高点)",
    "5~10% (轻微回调)",
    "10~20% (正常回调)",
    "20~35% (显著走弱)",
    "35~50% (深度回撤)",
    ">50% (崩盘级)",
]

WEIGHT = 0.25

# ============================================================
# 数据获取
# ============================================================
def fetch_data():
    print("指标2：HBM代理回撤（权重25%）")
    print("=" * 60)
    print(f"成分：SK海力士({WEIGHT_SK*100:.0f}%), 三星电子({WEIGHT_SAMSUNG*100:.0f}%)")
    print(f"回撤窗口：{LOOKBACK_DAYS} 个交易日")

    sk = yf.download(SK_HYNIX, period="2y", auto_adjust=True, progress=False)
    sam = yf.download(SAMSUNG, period="2y", auto_adjust=True, progress=False)

    if isinstance(sk.columns, pd.MultiIndex):
        sk = sk["Close"].iloc[:, 0].squeeze()
    else:
        sk = sk["Close"]
    if isinstance(sam.columns, pd.MultiIndex):
        sam = sam["Close"].iloc[:, 0].squeeze()
    else:
        sam = sam["Close"]

    # 对齐日期
    df = pd.DataFrame({"sk_hynix": sk, "samsung": sam}).dropna()
    print(f"对齐后数据条数：{len(df)} 个交易日\n")
    return df

# ============================================================
# 计算回撤
# ============================================================
def calc_drawdown(series, window):
    """滚动窗口最大回撤"""
    rolling_high = series.rolling(window=window, min_periods=1).max()
    drawdown = (series - rolling_high) / rolling_high * 100  # 负值，越大表示离高点越远
    return drawdown

def compute_score(dd_value):
    """单次映射：回撤 → 得分"""
    idx = np.digitize(dd_value, BINS) - 1
    idx = max(0, min(idx, len(SCORES) - 1))
    return SCORES[idx]


def map_series(dd_series):
    return [compute_score(abs(v)) for v in dd_series.values]


# ============================================================
# 主流程
# ============================================================
def run():
    df = fetch_data()

    # 各自回撤
    sk_dd = calc_drawdown(df["sk_hynix"], LOOKBACK_DAYS)
    sam_dd = calc_drawdown(df["samsung"], LOOKBACK_DAYS)

    # 加权合成回撤——全序列
    combined_series = abs(sk_dd) * WEIGHT_SK + abs(sam_dd) * WEIGHT_SAMSUNG

    # 最新回撤
    latest_sk_dd = sk_dd.iloc[-1]
    latest_sam_dd = sam_dd.iloc[-1]
    combined_dd = combined_series.iloc[-1]

    print(f"最新日期: {sk_dd.index[-1].strftime('%Y-%m-%d')}")
    print(f"  SK海力士 滚动252日高点回撤: {latest_sk_dd:.1f}%  (权重 {WEIGHT_SK*100:.0f}%)")
    print(f"  三星电子 滚动252日高点回撤: {latest_sam_dd:.1f}%  (权重 {WEIGHT_SAMSUNG*100:.0f}%)")

    print(f"\n加权合成回撤: {combined_dd:.1f}%")

    # 映射得分
    score = compute_score(combined_dd)
    idx = np.digitize(combined_dd, BINS) - 1
    idx = max(0, min(idx, len(SCORES) - 1))

    # ── 历史序列 ──
    all_scores = map_series(combined_series)
    history = all_scores[-30:]  # 最近30个交易日
    prev_score = all_scores[-6] if len(all_scores) >= 6 else score

    trend = "up" if score > prev_score else ("down" if score < prev_score else "flat")
    raw_label = f"回撤 {combined_dd:.1f}%"

    print(f"\n映射区间: {BIN_LABELS[idx]}")
    print(f"→ 风险预警得分: {score} / 100")
    weighted = score * WEIGHT
    print(f"  (权重 {WEIGHT*100:.0f}%，加权 {weighted:.1f})")
    return {"score": score, "prev_score": prev_score, "history": history,
            "raw_value": raw_label, "trend": trend}

if __name__ == "__main__":
    run()
