"""
============================================================
指标2：CSP资本开支景气度（权重25%）
数据来源：四大云厂商季度财报 CapEx，手动录入 CSV
============================================================
"""
import pandas as pd

CSV_PATH = "csp_capex_data.csv"
CSP_NAMES = ["Amazon", "Microsoft", "Google", "Meta"]
COLUMNS   = ["amzn_capex_bn", "msft_capex_bn", "googl_capex_bn", "meta_capex_bn"]

# ── 映射表：四家CSP CapEx平均YoY增速 → 景气度得分 ──
# （增速是每家自己跟自己比，口径纵向一致，信号不扭曲）
MAPPING = [
    (-999, -20,   0),
    (-20,  -10,  25),
    (-10,    0,  40),
    (  0,   20,  60),
    ( 20,   50,  75),
    ( 50,  100,  90),
    (100,  999, 100),
]


def fmt_quarter(dt):
    """把 Timestamp 转成 '2026-Q2' 格式"""
    return f"{dt.year}-Q{dt.quarter}"

QUARTER_MONTH = {"1":"01","2":"04","3":"07","4":"10"}

def load_data(path=CSV_PATH):
    df = pd.read_csv(path)
    # "2025-Q2" → "2025-04-01"（Q2从4月开始）
    def parse_q(s):
        y, q = s.split("-Q")
        return pd.to_datetime(f"{y}-{QUARTER_MONTH[q]}-01")
    df["quarter"] = df["quarter"].apply(parse_q)
    df = df.sort_values("quarter").set_index("quarter")
    return df


def compute_yoy_growth(df):
    """计算每家CSP的季度CapEx YoY增速，返回等权平均值"""
    growth_rates = {}
    latest = df.index[-1]
    year_ago = latest - pd.DateOffset(years=1)

    print(f"最新季度: {fmt_quarter(latest)}  vs  去年同期: {fmt_quarter(year_ago)}")
    print()

    for col, name in zip(COLUMNS, CSP_NAMES):
        if col in df.columns and year_ago in df.index:
            current = df.loc[latest, col]
            prior   = df.loc[year_ago, col]
            yoy = (current - prior) / prior * 100
            growth_rates[name] = yoy
            print(f"  {name:12s}  ${prior:.1f}B → ${current:.1f}B  增速 {yoy:+.0f}%")
        else:
            print(f"  {name:12s}  数据缺失，跳过")

    avg_growth = sum(growth_rates.values()) / len(growth_rates) if growth_rates else None
    return growth_rates, avg_growth


def map_score(avg_growth):
    """将平均YoY增速映射到0-100"""
    for lo, hi, score in MAPPING:
        if lo <= avg_growth < hi:
            return score, f"[{lo}, {hi})"
    return 100, "≥100"


def run():
    print("=" * 60)
    print("指标2：CSP资本开支景气度（权重25%）")
    print("=" * 60)

    df = load_data()
    print(f"已加载 {len(df)} 个季度数据\n")

    growth_rates, avg_growth = compute_yoy_growth(df)

    if avg_growth is None:
        print("\n[ERROR] 无法计算YoY增速，请检查CSV数据")
        return

    score, bucket = map_score(avg_growth)

    print(f"\n四家CSP平均YoY增速: {avg_growth:+.1f}%")
    print(f"映射区间: {bucket}")
    print(f"→ 景气度得分: {score} / 100")


if __name__ == "__main__":
    run()
