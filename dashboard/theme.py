"""Visual tokens for the Morandi instrumentation interface."""

from __future__ import annotations

import streamlit as st


def build_theme_css() -> str:
    return """
<style>
:root {
  --canvas: #F1EFE8;
  --surface: #FFFDF9;
  --surface-muted: #E8E5DC;
  --ink: #26322C;
  --ink-muted: #66716B;
  --border: #D9D6CC;
  --healthy: #718B7A;
  --evidence: #78909A;
  --warning: #B1815F;
  --failure: #A45F5F;
}
html, body, [class*="css"], [data-testid="stAppViewContainer"] {
  font-family: "IBM Plex Sans", "Noto Sans TC", "Microsoft JhengHei", sans-serif;
  color: var(--ink);
}
html { font-size: 18px; }
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 86% 0%, rgba(113,139,122,.11), transparent 28rem),
    linear-gradient(180deg, #F7F5EF 0, var(--canvas) 32rem);
}
[data-testid="stHeader"] { background: transparent; height: 1.5rem; }
[data-testid="stToolbar"] { opacity: .42; }
.block-container { max-width: 1500px; padding: .75rem 1.5rem 2rem; }
p, label, [data-testid="stMarkdownContainer"] { font-size: 18px; line-height: 1.5; }
h1, h2, h3 { color: var(--ink); letter-spacing: -.035em; }
h1 { font-size: clamp(1.75rem, 2vw, 2.05rem) !important; line-height: 1.12 !important; }
h2 { font-size: clamp(1.45rem, 2vw, 2rem) !important; }
h3 { font-size: 1.24rem !important; margin: 1.05rem 0 .4rem !important; }
.ops-kicker { color: #60736A; font-size: .875rem; letter-spacing: .12em; font-weight: 800; }
.brand-block { min-height:3.5rem; display:flex; flex-direction:column; justify-content:flex-end; }
.brand-title { font-size:1.08rem; font-weight:820; line-height:1.2; }
.brand-subtitle { color:var(--ink-muted); font-size:.944rem; line-height:1.35; }
.ops-heading { display:grid; grid-template-columns:minmax(0,38fr) minmax(0,62fr); gap:1.5rem; align-items:end; }
.ops-title { margin:0; font-size:clamp(1.75rem,2vw,2.05rem); line-height:1.12; font-weight:850; letter-spacing:-.03em; }
.ops-lede { max-width:none; color:var(--ink-muted); font-size:1rem; line-height:1.5; }
.ops-rule { height: 1px; background: linear-gradient(90deg, #87998F, transparent); margin: .6rem 0 .55rem; }
.source-line { display:flex; gap:.65rem; align-items:center; flex-wrap:wrap; margin:.1rem 0 .65rem; }
.source-badge { display:inline-flex; align-items:center; gap:.42rem; border-radius:999px; padding:.3rem .65rem; font-size:17px; font-weight:800; letter-spacing:.05em; }
.source-badge.demo { background:#F0DFC8; color:#715A3F; }
.source-badge.live { background:#DCE7DE; color:#355044; }
.source-badge.evidence { background:#DDE5E8; color:#405B65; }
.source-note { color:var(--ink-muted); font-size:17px; }
.metric-grid { display:grid; grid-template-columns:repeat(var(--metric-columns),minmax(0,1fr)); gap:0; margin:.1rem 0 .45rem; border-top:1px solid var(--border); border-bottom:1px solid var(--border); }
.metric-count-1 { --metric-columns:1; }
.metric-count-2 { --metric-columns:2; }
.metric-count-3 { --metric-columns:3; }
.metric-count-4 { --metric-columns:4; }
.metric-count-5 { --metric-columns:5; }
.metric-count-6 { --metric-columns:6; }
.metric-count-7 { --metric-columns:7; }
.metric-card { min-height:88px; display:grid; grid-template-columns:minmax(0,1fr) auto; grid-template-areas:"label value" "detail value"; column-gap:.8rem; align-items:center; padding:.68rem .85rem; border:0; border-left:1px solid var(--border); border-radius:0; background:transparent; box-shadow:none; }
.metric-card:first-child { border-left:0; }
.metric-label { grid-area:label; color:var(--ink-muted); font-size:17px; font-weight:800; letter-spacing:.055em; }
.metric-value { grid-area:value; margin:0; color:var(--ink); font-size:clamp(1.5rem,2vw,1.9rem); font-weight:820; line-height:1.1; font-variant-numeric:tabular-nums; }
.metric-detail { grid-area:detail; color:var(--ink-muted); font-size:17px; }
.status-card { padding:.75rem .15rem; border:0; border-bottom:1px solid var(--border); border-radius:0; background:transparent; }
.status-card strong { font-size:1rem; }
.status-card small { font-size:17px; line-height:1.45; }
.status-dot { display:inline-block; width:.58rem; height:.58rem; border-radius:50%; margin-right:.45rem; }
.status-dot.healthy { background:var(--healthy); box-shadow:0 0 0 4px rgba(113,139,122,.13); }
.status-dot.warning { background:var(--warning); box-shadow:0 0 0 4px rgba(177,129,95,.13); }
.status-dot.failure { background:var(--failure); box-shadow:0 0 0 4px rgba(164,95,95,.13); }
.callout { padding:.78rem .95rem; border-left:1px solid var(--evidence); border-radius:4px; background:rgba(255,253,249,.82); }
.callout.warning { border-left-color:var(--warning); }
.callout.failure { border-left-color:var(--failure); }
.callout-title { font-weight:800; margin-bottom:.2rem; }
.callout-copy { color:var(--ink-muted); font-size:17px; }
div[data-testid="stHorizontalBlock"] { gap:.65rem; }
div[role="radiogroup"] { gap:.38rem; padding:0; border:0; border-radius:0; background:transparent; }
div[role="radiogroup"] label { padding:.45rem .72rem; border-bottom:2px solid transparent; border-radius:0; }
div[role="radiogroup"] label:has(input:checked) { border-bottom-color:var(--healthy); background:rgba(113,139,122,.10); }
[data-testid="stDataFrame"] { border:1px solid var(--border); border-radius:4px; overflow:hidden; }
[data-testid="stMarkdownContainer"]:has(.chart-measure-key) { margin-bottom:-.15rem; }
.chart-measure-key { display:grid; grid-template-columns:repeat(var(--chart-key-columns),minmax(0,1fr)); align-items:center; gap:1rem; margin:.05rem 0 0; padding:0 .1rem; font-size:17px; font-weight:780; line-height:1.35; }
.chart-key-count-1 { --chart-key-columns:1; }
.chart-key-count-2 { --chart-key-columns:2; }
.chart-key-item { display:flex; align-items:center; gap:.52rem; min-width:0; }
.chart-key-item.request { color:#566F60; }
.chart-key-item.latency { color:#9A684A; }
.chart-key-item.neutral { color:var(--ink-muted); }
.chart-key-count-2 .chart-key-item:last-child { justify-content:flex-end; text-align:right; }
.chart-key-bar { flex:0 0 auto; width:1.05rem; height:.68rem; background:currentColor; }
.chart-key-line { position:relative; flex:0 0 auto; width:1.5rem; height:0; border-top:4px solid currentColor; }
.chart-key-line::after { content:""; position:absolute; top:-.34rem; left:.55rem; width:.48rem; height:.48rem; border-radius:50%; background:currentColor; }
.chart-key-item.request .chart-key-bar { background:#5F7F6B; }
.chart-key-item.latency .chart-key-line { border-top-color:#B56F45; }
.chart-key-item.latency .chart-key-line::after { background:#B56F45; }
[data-testid="stVegaLiteChart"] { margin:.1rem 0 .35rem; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { font-size:17px !important; line-height:1.45 !important; }
[data-testid="stExpander"] { border-color:var(--border); border-radius:4px; background:rgba(255,253,249,.66); }
.stButton button, .stDownloadButton button { min-height:2.6rem; border-radius:6px; font-weight:750; }
div[data-baseweb="select"] > div { border-radius:6px; }
*:focus-visible { outline:3px solid rgba(120,144,154,.52) !important; outline-offset:2px; }
@media (max-width: 1180px) {
  .metric-count-7 { --metric-columns:4; }
  .metric-count-7 .metric-card:nth-child(5) { border-left:0; }
  .metric-count-7 .metric-card:nth-child(n+5) { border-top:1px solid var(--border); }
}
@media (max-width: 760px) {
  html { font-size: 16px; }
  p, label, [data-testid="stMarkdownContainer"] { font-size:16px; line-height:1.5; }
  .block-container { padding: 1rem .9rem 2.25rem; }
  .ops-title, h1 { font-size:clamp(1.75rem, 7.4vw, 1.9rem) !important; }
  .metric-grid { grid-template-columns:repeat(2,minmax(0,1fr)); gap:0; }
  .metric-card { min-height:100px; display:block; }
  .metric-card:nth-child(odd) { border-left:0; }
  .metric-card:nth-child(even) { border-left:1px solid var(--border); }
  .metric-card:nth-child(n+3) { border-top:1px solid var(--border); }
  .metric-value { margin:.2rem 0 .08rem; }
  .ops-lede { font-size:1rem; }
  .source-badge, .source-note, .metric-label, .metric-detail, .callout-copy,
  [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p,
  .status-card small { font-size:15px !important; }
  .chart-measure-key { gap:.65rem; font-size:15px; }
}
@media (max-width: 860px) {
  .ops-heading { grid-template-columns:minmax(0,1fr); gap:.25rem; align-items:start; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration:.01ms !important; transition-duration:.01ms !important; }
}
</style>
"""


def apply_theme() -> None:
    st.markdown(build_theme_css(), unsafe_allow_html=True)
