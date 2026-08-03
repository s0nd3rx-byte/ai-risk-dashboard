"""
============================================================
AI风险预警指数 — 整合脚本
跑5个指标 → 计算加权总分 → 输出JSON（供HTML读取）
============================================================
"""
import json
import os
import sys
import datetime

# 添加项目目录到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from indicator_mag7_capex_ocf import run as run1, WEIGHT as W1
from indicator_hbm_drawdown import run as run2, WEIGHT as W2
from indicator_kospi_nasdaq_corr import run as run3, WEIGHT as W3
from indicator_ai_stock_corr import run as run4, WEIGHT as W4
from indicator_shiller_cape import run as run5, WEIGHT as W5


def run_all():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 60)
    print("  AI 风险预警指数 — 全指标汇总")
    print(f"  运行时间: {now}")
    print("=" * 60)
    print()

    results = []

    # ── 指标1 ──
    print("▶ 指标1：Mag7 capex/OCF（权重25%）")
    d1 = run1()
    results.append({"name": "Mag7 capex/OCF", "score": d1["score"], "weight": W1,
                    "weighted": d1["score"] * W1, "prev_score": d1["prev_score"],
                    "history": d1["history"], "raw_value": d1["raw_value"],
                    "trend": d1["trend"]})
    print()

    # ── 指标2 ──
    print("▶ 指标2：HBM代理回撤（权重25%）")
    d2 = run2()
    results.append({"name": "HBM代理回撤", "score": d2["score"], "weight": W2,
                    "weighted": d2["score"] * W2, "prev_score": d2["prev_score"],
                    "history": d2["history"], "raw_value": d2["raw_value"],
                    "trend": d2["trend"]})
    print()

    # ── 指标3 ──
    print("▶ 指标3：Kospi-Nasdaq 60日相关性（权重20%）")
    d3 = run3()
    results.append({"name": "Kospi-Nasdaq相关性", "score": d3["score"], "weight": W3,
                    "weighted": d3["score"] * W3, "prev_score": d3["prev_score"],
                    "history": d3["history"], "raw_value": d3["raw_value"],
                    "trend": d3["trend"]})
    print()

    # ── 指标4 ──
    print("▶ 指标4：AI股间价格相关性（权重20%）")
    d4 = run4()
    results.append({"name": "AI股间相关性", "score": d4["score"], "weight": W4,
                    "weighted": d4["score"] * W4, "prev_score": d4["prev_score"],
                    "history": d4["history"], "raw_value": d4["raw_value"],
                    "trend": d4["trend"]})
    print()

    # ── 指标5 ──
    print("▶ 指标5：Shiller CAPE（权重10%）")
    d5 = run5()
    results.append({"name": "Shiller CAPE", "score": d5["score"], "weight": W5,
                    "weighted": d5["score"] * W5, "prev_score": d5["prev_score"],
                    "history": d5["history"], "raw_value": d5["raw_value"],
                    "trend": d5["trend"]})
    print()

    # ── 加权总分 ──
    total_score = sum(r["weighted"] for r in results)

    # 警报等级
    if total_score >= 80:
        alert = "⚠️ 高风险 — 触发减仓警戒线"
        alert_level = "danger"
    elif total_score >= 65:
        alert = "⚡ 中高风险 — 密切关注"
        alert_level = "warning"
    elif total_score >= 40:
        alert = "● 中等风险 — 正常"
        alert_level = "normal"
    else:
        alert = "✅ 低风险 — 安全区间"
        alert_level = "safe"

    print("=" * 60)
    print(f"  AI风险预警指数: {total_score:.1f} / 100")
    print(f"  {alert}")
    print("=" * 60)

    # ── 输出 JSON ──
    output = {
        "timestamp": now,
        "total_score": round(total_score, 1),
        "alert": alert,
        "alert_level": alert_level,
        "indicators": results,
    }

    base_dir = os.path.dirname(os.path.abspath(__file__))

    json_path = os.path.join(base_dir, "dashboard_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nJSON 已输出: {json_path}")

    # ── 同步更新 index.html 内嵌数据 ──
    html_path = os.path.join(base_dir, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        data_json_str = json.dumps(output, ensure_ascii=False)
        # 替换 DEMO_DATA 占位
        import re
        html = re.sub(
            r'const DEMO_DATA = \{.*?\};',
            f'const DEMO_DATA = {data_json_str};',
            html,
            flags=re.DOTALL
        )
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML 仪表盘已刷新: {html_path}")

    return output


if __name__ == "__main__":
    run_all()
