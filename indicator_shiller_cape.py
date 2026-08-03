"""
============================================================
指标5：Shiller CAPE（权重10%）
数据源：本地 shiller_cape.csv（月度手动更新）
逻辑：CAPE绝对值越高 → 估值泡沫风险越大 → 得分越高
映射：7档绝对值区间（0/25/40/60/75/90/100）
============================================================
"""
import os
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

WEIGHT = 0.10

# ── 映射：CAPE绝对值 → 风险得分 ──
CAPE_BINS = [
    (15,    0),
    (20,   25),
    (25,   40),
    (30,   60),
    (35,   75),
    (40,   90),
    (float("inf"), 100),
]

def compute_score(cape_value):
    for threshold, score in CAPE_BINS:
        if cape_value < threshold:
            return score
    return 100


def run():
    print("=" * 60)
    print("指标5：Shiller CAPE（权重10%）")
    print("=" * 60)

    local_path = os.path.join(os.path.dirname(__file__), "shiller_cape.csv")
    if not os.path.exists(local_path):
        print("错误：shiller_cape.csv 不存在，请先创建该文件")
        return {"score": 0, "prev_score": 0, "history": [], "raw_value": "N/A", "trend": "flat"}

    df = pd.read_csv(local_path)
    cape = df["CAPE"].iloc[-1]
    cape_date = df["Date"].iloc[-1] if "Date" in df.columns else "未知"

    print(f"[数据源] 本地 shiller_cape.csv")
    print(f"  日期: {cape_date}")
    print(f"  CAPE: {cape:.2f}")

    score = compute_score(cape)

    # ── 历史序列（CSV 里的所有行） ──
    history_scores = [compute_score(v) for v in df["CAPE"].values]
    prev_score = history_scores[-2] if len(history_scores) >= 2 else score
    # 取最近12个月用于折线图
    history = history_scores[-12:]

    trend = "up" if score > prev_score else ("down" if score < prev_score else "flat")
    raw_label = f"CAPE {cape:.2f}"

    print()
    print(f"→ 风险预警得分: {score} / 100")

    weighted = score * WEIGHT
    print(f"  (权重 {WEIGHT*100:.0f}%，加权 {weighted:.1f})")

    print()
    print("--- RESULT ---")
    print(f"CAPE_VALUE:{cape:.2f}")
    print(f"SCORE:{score}")
    print(f"WEIGHTED:{weighted:.1f}")
    return {"score": score, "prev_score": prev_score, "history": history,
            "raw_value": raw_label, "trend": trend}


if __name__ == "__main__":
    run()
