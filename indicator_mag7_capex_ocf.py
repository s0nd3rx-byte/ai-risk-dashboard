"""
============================================================
指标1：Mag7 capex/OCF（权重25%）
逻辑：Mag7等权 capex/OCF → 7档区间 → 0-100
      AAPL、NVDA单独标注双口径
数据源：yfinance quarterly_cashflow
修复：按日历季度对齐（不再盲取列序），解决AMZN因
      财报截止日不同导致的前季偏差
============================================================
"""
import yfinance as yf
import pandas as pd
import numpy as np

MAG7_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
WEIGHT = 0.25

# 映射区间（文档已确认）
BINS = [
    (-np.inf, 0.30,  0),
    (0.30,    0.50, 25),
    (0.50,    0.70, 40),
    (0.70,    0.90, 60),
    (0.90,    1.10, 75),
    (1.10,    1.50, 90),
    (1.50,    np.inf, 100),
]


def map_score(value):
    for lo, hi, score in BINS:
        if lo <= value < hi:
            return score
    return 100  # fallback


# ─── 字段名匹配工具 ───
CAPEX_CANDIDATES = [
    "Capital Expenditure", "CapitalExpenditure",
    "CapitalExpenditures", "Capital Expenditures",
    "PurchaseOfBusiness", "Purchase Of Business",
    "PurchaseOfPPE", "Purchase Of P P E",
]

OCF_CANDIDATES = [
    "Operating Cash Flow", "OperatingCashFlow",
    "Cash Flow From Operating Activities",
    "CashFlowFromOperatingActivities",
    "Total Cash From Operating Activities",
]


def find_field(df, candidates, keywords=None):
    """在 df.index 中找字段名"""
    for c in candidates:
        if c in df.index:
            return c
    if keywords:
        for idx in df.index:
            idx_lower = idx.lower()
            if all(k in idx_lower for k in keywords):
                return idx
    return None


def get_available_quarters(ticker):
    """返回 {日历季度标签: (列名, date_obj)} 映射"""
    stock = yf.Ticker(ticker)
    cf = stock.quarterly_cashflow
    if cf is None or cf.empty:
        return {}, None, None

    capex_name = find_field(cf, CAPEX_CANDIDATES, ["capital", "expenditure"])
    ocf_name = find_field(cf, OCF_CANDIDATES, ["operating"])
    if capex_name is None or ocf_name is None:
        return {}, None, None

    quarters = {}
    for col in cf.columns:
        # 列名形如 "2026-06-30" 的 Timestamp
        d = pd.Timestamp(col)
        # 标准化为日历季度: "2026-Q2"
        q_label = f"{d.year}-Q{(d.month - 1) // 3 + 1}"
        quarters[q_label] = (col, d, float(abs(cf.loc[capex_name, col])),
                             float(abs(cf.loc[ocf_name, col])))
    return quarters, capex_name, ocf_name


def find_common_quarters(all_quarter_maps):
    """找到所有公司共同拥有的日历季度，从新到旧排序"""
    common = None
    for q_map in all_quarter_maps:
        qs = set(q_map.keys())
        if common is None:
            common = qs
        else:
            common = common & qs
    if not common:
        return []
    # 排序：最新的在前
    def sort_key(q):
        y, qn = q.split("-Q")
        return (int(y), int(qn))
    return sorted(common, key=sort_key, reverse=True)


def run():
    print("=" * 60)
    print("指标1：Mag7 capex/OCF（权重25%）")
    print("=" * 60)
    print(f"Mag7成分：{', '.join(MAG7_TICKERS)}")
    print()

    # ── 1. 拉每家全部可用季度 ──
    all_qmaps = {}
    for ticker in MAG7_TICKERS:
        qmap, _, _ = get_available_quarters(ticker)
        if qmap:
            all_qmaps[ticker] = qmap
            print(f"   {ticker:6s}  找到 {len(qmap)} 个季度: {sorted(qmap.keys())}")
        else:
            print(f"   {ticker:6s}  无数据，跳过")

    # ── 2. 找共同日历季度 ──
    common_qs = find_common_quarters(list(all_qmaps.values()))
    if len(common_qs) < 2:
        print(f"\n  共同季度不足（{len(common_qs)}个），退回旧逻辑")
        # 退回到 col_idx 方式
        return _fallback_run()

    print(f"\n共同日历季度（最新→最旧）: {common_qs}")

    # ── 3. 当前季度 = common_qs[0]，前季 = common_qs[1] ──
    cur_q = common_qs[0]
    prev_q = common_qs[1]

    ratios = {}
    prev_ratios = {}
    quarters = {}
    prev_quarters = {}

    for ticker in MAG7_TICKERS:
        qmap = all_qmaps.get(ticker, {})
        if cur_q in qmap:
            col, d, capex_v, ocf_v = qmap[cur_q]
            ratios[ticker] = capex_v / ocf_v if ocf_v != 0 else None
            quarters[ticker] = cur_q
        else:
            ratios[ticker] = None
            quarters[ticker] = "N/A"

    for ticker in MAG7_TICKERS:
        qmap = all_qmaps.get(ticker, {})
        if prev_q in qmap:
            _, _, capex_v, ocf_v = qmap[prev_q]
            prev_ratios[ticker] = capex_v / ocf_v if ocf_v != 0 else None
            prev_quarters[ticker] = prev_q
        else:
            prev_ratios[ticker] = None
            prev_quarters[ticker] = "N/A"

    # ── 4. 输出当前季度 ──
    for ticker in MAG7_TICKERS:
        r = ratios.get(ticker)
        if r is not None:
            print(f"  {ticker:6s}  capex/OCF = {r:.2f}  ({quarters[ticker]})")
        else:
            print(f"  {ticker:6s}  数据缺失")

    valid_ratios = {k: v for k, v in ratios.items() if v is not None}
    valid_prev = {k: v for k, v in prev_ratios.items() if v is not None}

    all_avg = np.mean(list(valid_ratios.values()))
    all_score = map_score(all_avg)

    prev_avg = np.mean(list(valid_prev.values())) if valid_prev else all_avg
    prev_score = map_score(prev_avg)

    # ── 双口径 ──
    exclude = {"AAPL", "NVDA"}
    trimmed = {k: v for k, v in valid_ratios.items() if k not in exclude}
    trimmed_avg = np.mean(list(trimmed.values())) if trimmed else all_avg
    trimmed_score = map_score(trimmed_avg)

    print()
    print(f"当前季度: {cur_q}")
    print(f"Mag7等权 capex/OCF: {all_avg:.2%}")
    print(f"→ 风险预警得分（全7家）: {all_score} / 100")
    print()
    print(f"剔除AAPL+NVDA后 Mag5等权 capex/OCF: {trimmed_avg:.2%}")
    print(f"→ 风险预警得分（Mag5）: {trimmed_score} / 100")
    print()

    # ── 诊断：前季对比 ──
    print("─" * 60)
    print(f"[诊断] 前季 ({prev_q}) vs 当季 ({cur_q}) 逐家对比：")
    for ticker in MAG7_TICKERS:
        r = ratios.get(ticker)
        pr = prev_ratios.get(ticker)
        if r is not None and pr is not None:
            delta = r - pr
            print(f"  {ticker:6s}  {pr:.2f} → {r:.2f}  (变动 {delta:+.2f})")
        elif pr is not None:
            print(f"  {ticker:6s}  前季 {pr:.2f} → 当季缺失")
        elif r is not None:
            print(f"  {ticker:6s}  前季缺失 → 当季 {r:.2f}")
        else:
            print(f"  {ticker:6s}  双季缺失")
    print(f"  前季等权均值: {prev_avg:.2%} → 得分 {prev_score}")
    print(f"  当季等权均值: {all_avg:.2%} → 得分 {all_score}")
    print(f"  变动: {prev_score} → {all_score}  ({all_score - prev_score:+d})")
    print("─" * 60)
    print()
    print(f"[最终] 指标1得分: {all_score} / 100（权重25%，加权 {all_score * WEIGHT:.1f}）")

    # ── 历史序列 ──
    history_scores = []
    # 从旧到新取最多4个历史季度（排除当前）
    for q in reversed(common_qs[1:5]):  # 最多取4季历史
        q_ratios = {}
        for ticker in MAG7_TICKERS:
            qmap = all_qmaps.get(ticker, {})
            if q in qmap:
                _, _, capex_v, ocf_v = qmap[q]
                if ocf_v != 0:
                    q_ratios[ticker] = capex_v / ocf_v
        if len(q_ratios) >= 4:
            history_scores.append(map_score(np.mean(list(q_ratios.values()))))
    history_scores.append(all_score)

    trend = "up" if all_score > prev_score else ("down" if all_score < prev_score else "flat")
    if abs(all_score - prev_score) <= 5:
        trend = "flat"  # 5分以内算持平

    raw_label = f"{all_avg:.1%} (Mag5: {trimmed_avg:.1%})"

    return {"score": all_score, "prev_score": prev_score, "history": history_scores,
            "raw_value": raw_label, "trend": trend}


def _fallback_run():
    """旧col_idx后备方案"""
    # 仅容错，不详细展开
    print("[fallback] 使用列序盲取")
    ratios = {}
    for ticker in MAG7_TICKERS:
        stock = yf.Ticker(ticker)
        cf = stock.quarterly_cashflow
        if cf is None or cf.empty or len(cf.columns) < 2:
            continue
        capex_name = find_field(cf, CAPEX_CANDIDATES, ["capital", "expenditure"])
        ocf_name = find_field(cf, OCF_CANDIDATES, ["operating"])
        if capex_name is None or ocf_name is None:
            continue
        cv = abs(float(cf.loc[capex_name, cf.columns[0]]))
        ov = abs(float(cf.loc[ocf_name, cf.columns[0]]))
        if ov != 0:
            ratios[ticker] = cv / ov
    if not ratios:
        return {"score": 0, "prev_score": 0, "history": [], "raw_value": "N/A", "trend": "flat"}
    avg = np.mean(list(ratios.values()))
    sc = map_score(avg)
    return {"score": sc, "prev_score": sc, "history": [sc], "raw_value": f"{avg:.1%}", "trend": "flat"}


if __name__ == "__main__":
    run()
