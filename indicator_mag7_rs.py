"""
============================================================
指标1：Mag7相对强度（权重25%）
方法：涨跌幅差值累加法
  - Mag7等权日涨跌幅均值 vs SPY日涨跌幅
  - 每日差值累加构建RS曲线
  - 当前RS - 52周前RS = YoY累计超额收益
  - YoY超额收益映射至0-100景气度得分
============================================================
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# ============================================================
# 配置
# ============================================================
MAG7_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
BENCHMARK     = "SPY"
LOOKBACK_YEARS = 2       # 拉取数据年数（含缓冲）
TRADING_DAYS   = 252     # 一年交易日，YoY窗口

# 映射表：(下限, 上限, 得分) ，上限可为 None 表示无上限
# YoY超额收益 = 过去252个交易日Mag7相对SPY的累计超额涨跌幅（百分点）
SCORE_BRACKETS = [
    ( -99,  -20,   0),
    ( -20,  -10,  25),
    ( -10,    0,  40),
    (   0,   10,  60),
    (  10,   20,  75),
    (  20,   30,  90),
    (  30,   99, 100),
]


# ============================================================
# 核心逻辑
# ============================================================

def fetch_data(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """批量拉取日线Adj Close，返回 (日期, 各列Adj Close) 的DataFrame"""
    raw = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
    )

    # ---- 诊断：看原始列结构 ----
    print(f"[DIAG] 原始列类型: {type(raw.columns)}")
    print(f"[DIAG] 原始列名:   {raw.columns.tolist() if not isinstance(raw.columns, pd.MultiIndex) else [list(c) for c in raw.columns.values]}")
    print(f"[DIAG] 列中是否有重复: {raw.columns.has_duplicates if hasattr(raw.columns, 'has_duplicates') else 'N/A'}")
    print(f"[DIAG] 索引是否有重复: {raw.index.has_duplicates}")
    print()

    if raw.empty:
        raise RuntimeError("yfinance 返回空数据，请检查网络或代码")

    # ---- 处理列 ----
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(-1)
        print(f"[DIAG] MultiIndex展平后列名: {raw.columns.tolist()}")
        print(f"[DIAG] 展平后列重复: {raw.columns.has_duplicates}")

    # ---- 去重 ----
    raw = raw[~raw.index.duplicated(keep="first")]
    raw = raw.loc[:, ~raw.columns.duplicated(keep="first")]

    # ---- 只保留需要的列 ----
    found = [t for t in tickers if t in raw.columns]
    raw = raw[found]
    missing = set(tickers) - set(found)
    if missing:
        print(f"[WARNING] 以下标的未在返回数据中: {missing}")
    print(f"[DIAG] 最终列名: {raw.columns.tolist()}，重复: {raw.columns.has_duplicates}")
    print()

    return raw


def calc_rs_curve(prices: pd.DataFrame) -> pd.Series:
    """
    涨跌幅差值累加法构建RS曲线
    - prices: 列 = MAG7_TICKERS + ["SPY"] (统一用收盘价)
    - 返回: RS曲线Series（起点=0）
    """
    # 日涨跌幅（%）
    returns = prices.pct_change().dropna()

    # Mag7等权涨跌幅均值
    mag7_ret = returns[MAG7_TICKERS].mean(axis=1)

    # 每日差值 = Mag7均值 - SPY
    daily_diff = mag7_ret - returns[BENCHMARK]

    # 累加（从0开始）
    rs_curve = daily_diff.cumsum()

    # 将累计值转为百分点（涨跌幅本身已是小数，累加后乘100）
    rs_curve = rs_curve * 100

    rs_curve.name = "RS"
    return rs_curve


def map_to_score(yoy_change: float) -> int:
    """按映射表将YoY变化率映射为0-100得分"""
    for lo, hi, score in SCORE_BRACKETS:
        if yoy_change >= lo and yoy_change < hi:
            return score
    return 0  # 兜底


def run():
    # ---- 时间窗口 ----
    end_date = datetime.now()
    start_date = end_date - timedelta(days=int(LOOKBACK_YEARS * 366))

    print("=" * 60)
    print("指标1：Mag7相对强度（权重25%）")
    print("=" * 60)
    print(f"数据范围：{start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    print(f"Mag7成分：{', '.join(MAG7_TICKERS)}")
    print(f"基准：{BENCHMARK}")
    print()

    # ---- 拉取数据 ----
    tickers = MAG7_TICKERS + [BENCHMARK]
    prices = fetch_data(tickers, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    print(f"实际数据条数：{len(prices)} 个交易日")

    # ---- 构建RS曲线 ----
    rs = calc_rs_curve(prices)
    print(f"RS曲线范围：{rs.min():.2f} ~ {rs.max():.2f}")

    # ---- YoY变化 ----
    # 确保有足够数据
    if len(rs) < TRADING_DAYS + 5:
        print(f"[WARNING] 有效数据不足252个交易日（仅{len(rs)}条），YoY结果仅供参考")

    current_rs = rs.iloc[-1]
    yoy_ago_rs = rs.iloc[-TRADING_DAYS - 1] if len(rs) > TRADING_DAYS else rs.iloc[0]
    yoy_change = current_rs - yoy_ago_rs

    # ---- 映射得分 ----
    score = map_to_score(yoy_change)

    # ---- 输出 ----
    print()
    print(f"当前RS值（累计超额收益）：{current_rs:.2f} 百分点")
    print(f"52周前RS值：              {yoy_ago_rs:.2f} 百分点")
    print(f"YoY变化（过去一年超额收益）：{yoy_change:+.2f} 百分点")
    print(f"→ 景气度得分：{score} / 100")
    print()
    print("映射区间参考：")
    for lo, hi, s in SCORE_BRACKETS:
        hi_str = f"{hi:+.0f}" if hi is not None else "+∞"
        marker = " ◀◀ 当前落在此区间" if s == score else ""
        print(f"  [{lo:+.0f}, {hi_str}) → {s:3d}分{marker}")
    print("=" * 60)

    return {
        "score": score,
        "current_rs": round(current_rs, 2),
        "yoy_ago_rs": round(yoy_ago_rs, 2),
        "yoy_change": round(yoy_change, 2),
    }


if __name__ == "__main__":
    run()
