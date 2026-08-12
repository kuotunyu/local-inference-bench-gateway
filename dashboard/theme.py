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
html { font-size: 16px; }
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 86% 0%, rgba(113,139,122,.11), transparent 28rem),
    linear-gradient(180deg, #F7F5EF 0, var(--canvas) 32rem);
}
[data-testid="stHeader"] { background: transparent; height: 2rem; }
[data-testid="stToolbar"] { opacity: .42; }
.block-container { max-width: 1480px; padding: 2.2rem 2.4rem 4rem; }
p, label, [data-testid="stMarkdownContainer"] { font-size: 16px; line-height: 1.6; }
h1, h2, h3 { color: var(--ink); letter-spacing: -.035em; }
h1 { font-size: clamp(2rem, 3.3vw, 3.55rem) !important; line-height: 1.06 !important; }
h2 { font-size: clamp(1.45rem, 2vw, 2rem) !important; }
h3 { font-size: 1.12rem !important; }
.ops-kicker { color: #60736A; font-size: .78rem; letter-spacing: .16em; font-weight: 800; }
.ops-title { margin: .35rem 0 .45rem; font-size: clamp(2rem, 3.3vw, 3.55rem); line-height: 1.06; font-weight: 850; letter-spacing: -.045em; }
.ops-lede { max-width: 52rem; color: var(--ink-muted); font-size: 1.05rem; }
.ops-rule { height: 1px; background: linear-gradient(90deg, #87998F, transparent); margin: 1.2rem 0 1.1rem; }
.source-line { display:flex; gap:.65rem; align-items:center; flex-wrap:wrap; margin:.2rem 0 1rem; }
.source-badge { display:inline-flex; align-items:center; gap:.42rem; border-radius:999px; padding:.38rem .7rem; font-size:.78rem; font-weight:800; letter-spacing:.06em; }
.source-badge.demo { background:#F0DFC8; color:#715A3F; }
.source-badge.live { background:#DCE7DE; color:#355044; }
.source-badge.evidence { background:#DDE5E8; color:#405B65; }
.source-note { color:var(--ink-muted); font-size:.88rem; }
.metric-card { min-height: 126px; padding: 1.05rem 1.08rem; border:1px solid var(--border); border-radius:16px; background:rgba(255,253,249,.9); box-shadow:0 8px 24px rgba(38,50,44,.045); }
.metric-label { color:var(--ink-muted); font-size:.72rem; font-weight:800; letter-spacing:.1em; }
.metric-value { margin:.45rem 0 .15rem; color:var(--ink); font-size:clamp(1.5rem,2.3vw,2.2rem); font-weight:820; line-height:1.1; font-variant-numeric:tabular-nums; }
.metric-detail { color:var(--ink-muted); font-size:.8rem; }
.status-card { padding:1rem 1.05rem; border:1px solid var(--border); border-radius:14px; background:var(--surface); }
.status-card strong { font-size:1rem; }
.status-dot { display:inline-block; width:.58rem; height:.58rem; border-radius:50%; margin-right:.45rem; }
.status-dot.healthy { background:var(--healthy); box-shadow:0 0 0 4px rgba(113,139,122,.13); }
.status-dot.warning { background:var(--warning); box-shadow:0 0 0 4px rgba(177,129,95,.13); }
.status-dot.failure { background:var(--failure); box-shadow:0 0 0 4px rgba(164,95,95,.13); }
.callout { padding:1rem 1.1rem; border-left:4px solid var(--evidence); border-radius:4px 13px 13px 4px; background:rgba(255,253,249,.82); }
.callout.warning { border-left-color:var(--warning); }
.callout.failure { border-left-color:var(--failure); }
.callout-title { font-weight:800; margin-bottom:.2rem; }
.callout-copy { color:var(--ink-muted); font-size:.92rem; }
div[data-testid="stHorizontalBlock"] { gap:.8rem; }
div[role="radiogroup"] { gap:.38rem; padding:.28rem; border:1px solid var(--border); border-radius:13px; background:rgba(255,253,249,.78); }
div[role="radiogroup"] label { padding:.45rem .72rem; border-radius:9px; }
div[role="radiogroup"] label:has(input:checked) { background:#DDE5DF; }
[data-testid="stDataFrame"] { border:1px solid var(--border); border-radius:14px; overflow:hidden; }
[data-testid="stExpander"] { border-color:var(--border); border-radius:14px; background:rgba(255,253,249,.66); }
.stButton button, .stDownloadButton button { min-height:2.6rem; border-radius:11px; font-weight:750; }
*:focus-visible { outline:3px solid rgba(120,144,154,.52) !important; outline-offset:2px; }
@media (max-width: 760px) {
  .block-container { padding: 1.4rem 1rem 3rem; }
  .metric-card { min-height:112px; }
  .ops-lede { font-size:1rem; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration:.01ms !important; transition-duration:.01ms !important; }
}
</style>
"""


def apply_theme() -> None:
    st.markdown(build_theme_css(), unsafe_allow_html=True)
