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
html { font-size: 17px; }
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 86% 0%, rgba(113,139,122,.11), transparent 28rem),
    linear-gradient(180deg, #F7F5EF 0, var(--canvas) 32rem);
}
[data-testid="stHeader"] { background: transparent; height: 1.5rem; }
[data-testid="stToolbar"] { opacity: .42; }
.block-container { max-width: 1500px; padding: 1.25rem 2rem 2.5rem; }
p, label, [data-testid="stMarkdownContainer"] { font-size: 17px; line-height: 1.55; }
h1, h2, h3 { color: var(--ink); letter-spacing: -.035em; }
h1 { font-size: clamp(2.15rem, 2.7vw, 2.65rem) !important; line-height: 1.08 !important; }
h2 { font-size: clamp(1.45rem, 2vw, 2rem) !important; }
h3 { font-size: 1.24rem !important; margin: 1.25rem 0 .45rem !important; }
.ops-kicker { color: #60736A; font-size: .875rem; letter-spacing: .12em; font-weight: 800; }
.ops-title { margin: .15rem 0 .25rem; font-size: clamp(2.15rem, 2.7vw, 2.65rem); line-height: 1.08; font-weight: 850; letter-spacing: -.035em; }
.ops-lede { max-width: 65rem; color: var(--ink-muted); font-size: 1rem; line-height:1.5; }
.ops-rule { height: 1px; background: linear-gradient(90deg, #87998F, transparent); margin: .75rem 0 .7rem; }
.source-line { display:flex; gap:.65rem; align-items:center; flex-wrap:wrap; margin:.1rem 0 .65rem; }
.source-badge { display:inline-flex; align-items:center; gap:.42rem; border-radius:999px; padding:.3rem .65rem; font-size:.875rem; font-weight:800; letter-spacing:.05em; }
.source-badge.demo { background:#F0DFC8; color:#715A3F; }
.source-badge.live { background:#DCE7DE; color:#355044; }
.source-badge.evidence { background:#DDE5E8; color:#405B65; }
.source-note { color:var(--ink-muted); font-size:.875rem; }
.metric-card { min-height: 108px; padding: .82rem .95rem; border:1px solid var(--border); border-radius:14px; background:rgba(255,253,249,.92); box-shadow:0 7px 20px rgba(38,50,44,.04); }
.metric-label { color:var(--ink-muted); font-size:.875rem; font-weight:800; letter-spacing:.075em; }
.metric-value { margin:.28rem 0 .1rem; color:var(--ink); font-size:clamp(1.5rem,2vw,2rem); font-weight:820; line-height:1.1; font-variant-numeric:tabular-nums; }
.metric-detail { color:var(--ink-muted); font-size:.875rem; }
.status-card { padding:.8rem .95rem; border:1px solid var(--border); border-radius:14px; background:var(--surface); }
.status-card strong { font-size:1rem; }
.status-dot { display:inline-block; width:.58rem; height:.58rem; border-radius:50%; margin-right:.45rem; }
.status-dot.healthy { background:var(--healthy); box-shadow:0 0 0 4px rgba(113,139,122,.13); }
.status-dot.warning { background:var(--warning); box-shadow:0 0 0 4px rgba(177,129,95,.13); }
.status-dot.failure { background:var(--failure); box-shadow:0 0 0 4px rgba(164,95,95,.13); }
.callout { padding:.78rem .95rem; border-left:1px solid var(--evidence); border-radius:12px; background:rgba(255,253,249,.82); }
.callout.warning { border-left-color:var(--warning); }
.callout.failure { border-left-color:var(--failure); }
.callout-title { font-weight:800; margin-bottom:.2rem; }
.callout-copy { color:var(--ink-muted); font-size:.9rem; }
div[data-testid="stHorizontalBlock"] { gap:.65rem; }
div[role="radiogroup"] { gap:.38rem; padding:.28rem; border:1px solid var(--border); border-radius:13px; background:rgba(255,253,249,.78); }
div[role="radiogroup"] label { padding:.45rem .72rem; border-radius:9px; }
div[role="radiogroup"] label:has(input:checked) { background:#DDE5DF; }
[data-testid="stDataFrame"] { border:1px solid var(--border); border-radius:14px; overflow:hidden; }
[data-testid="stVegaLiteChart"] { margin:.1rem 0 .35rem; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { font-size:.875rem !important; line-height:1.45 !important; }
[data-testid="stExpander"] { border-color:var(--border); border-radius:14px; background:rgba(255,253,249,.66); }
.stButton button, .stDownloadButton button { min-height:2.6rem; border-radius:11px; font-weight:750; }
*:focus-visible { outline:3px solid rgba(120,144,154,.52) !important; outline-offset:2px; }
@media (max-width: 760px) {
  html { font-size: 16px; }
  .block-container { padding: 1rem .9rem 2.25rem; }
  .ops-title, h1 { font-size:clamp(1.85rem, 8vw, 2.05rem) !important; }
  .metric-card { min-height:100px; }
  .ops-lede { font-size:1rem; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration:.01ms !important; transition-duration:.01ms !important; }
}
</style>
"""


def apply_theme() -> None:
    st.markdown(build_theme_css(), unsafe_allow_html=True)
