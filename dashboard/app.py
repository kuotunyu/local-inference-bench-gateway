"""Streamlit dashboard over the gateway's SQLite request log.

Run: streamlit run dashboard/app.py
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(os.environ.get("GATEWAY_DB_PATH", "data/gateway.db"))

st.set_page_config(page_title="Gateway Dashboard", layout="wide")
st.title("本地推論閘道 — 請求儀表板")

if st.button("重新整理"):
    st.rerun()

if not DB_PATH.exists():
    st.warning(f"找不到資料庫：{DB_PATH}。請先啟動閘道並送出至少一個請求。")
    st.stop()

conn = sqlite3.connect(str(DB_PATH))
requests_df = pd.read_sql_query("SELECT * FROM requests ORDER BY id DESC", conn)
failover_df = pd.read_sql_query("SELECT * FROM failover_events ORDER BY id DESC", conn)
conn.close()

if requests_df.empty:
    st.info("尚無請求紀錄。")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("總請求數", len(requests_df))
success_rate = requests_df["success"].mean() * 100
col2.metric("成功率", f"{success_rate:.1f}%")
col3.metric("平均總延遲", f"{requests_df['total_latency_ms'].mean():.0f} ms")
col4.metric("Failover 事件數", len(failover_df))

st.subheader("各別名統計")
by_alias = (
    requests_df.groupby("alias")
    .agg(
        requests=("id", "count"),
        success_rate_pct=("success", lambda s: round(s.mean() * 100, 1)),
        median_latency_ms=("total_latency_ms", "median"),
        p95_latency_ms=("total_latency_ms", lambda s: s.quantile(0.95)),
        total_completion_tokens=("completion_tokens", "sum"),
    )
    .reset_index()
)
st.dataframe(by_alias, use_container_width=True)

st.subheader("延遲分布（依別名）")
st.bar_chart(requests_df, x="alias", y="total_latency_ms", stack=False)

st.subheader("最近請求")
display_cols = [
    "timestamp",
    "alias",
    "backend_name",
    "model",
    "stream",
    "status_code",
    "success",
    "prompt_tokens",
    "completion_tokens",
    "ttft_ms",
    "total_latency_ms",
    "error_message",
]
st.dataframe(requests_df[display_cols].head(200), use_container_width=True)

st.subheader("Failover 事件")
if failover_df.empty:
    st.caption("尚無 failover 事件（所有請求都由主要後端成功處理）。")
else:
    st.dataframe(failover_df, use_container_width=True)
