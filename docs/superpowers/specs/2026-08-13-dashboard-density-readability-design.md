# Operations Console Density & Readability Design

## Objective

Refine the existing Operations Console without changing its data semantics or four-view
information architecture. The interface should read as an operational instrument: compact at the
page level, generous where data visualization needs room, and comfortable for sustained reading.

## Approved direction: Operational Canvas

Keep the restrained Morandi visual identity and replace the current oversized editorial hero plus
small paired charts with a denser operational hierarchy.

### Typography

- Reduce the page title from the current 3.55 rem ceiling to a desktop range of 2.15–2.65 rem.
- Keep section headings visually distinct at 1.2–1.3 rem.
- Raise primary body copy to 17 px with a 1.55 line height.
- Keep supporting copy, captions, source notes, KPI labels, and chart labels at 14 px or larger.
- Preserve tabular numerals for KPI values and the current Traditional Chinese / original technical
  term language convention.

### Density and spacing

- Reduce the app shell top/bottom padding and tighten the title, divider, source badge, KPI, and
  section transitions.
- Retain whitespace only when it separates task groups or improves chart comprehension.
- Reduce KPI card height while preserving readable labels and values.
- Keep navigation and source/window controls in the first viewport on desktop.
- Do not add new wrappers, nested cards, or decorative hierarchy.

### Chart layout

- Replace compact Streamlit convenience charts with reusable Altair chart helpers so axis, legend,
  tooltip, line, point, bar, and title sizes are explicit.
- Give primary trend charts a full-width canvas and 380–420 px height.
- Place secondary charts in a two-column grid only when each retains at least half of the available
  desktop width; stack them on narrow screens through Streamlit's responsive columns.
- Use visible point marks on low-cardinality trends, 2.5–3 px lines, 15 px axis titles, 14 px tick
  labels, and 14 px legends.
- Keep the existing Morandi semantic colors and avoid decorative chart chrome.

### View-specific composition

- **Overview:** full-width request-volume and P95-latency trend chart; Backend Health moves beside
  Alias Routing below the chart. KPI row remains the scan-first summary.
- **Routing & Reliability:** routing and health remain paired; Error Categories becomes a larger
  horizontal bar chart, with Backpressure beside it only when the chart retains useful width.
- **Requests:** filters stay compact; summary cards use two dense rows; request table grows to use
  the remaining canvas.
- **Benchmark Evidence:** throughput and P50/P95 TTFT become separate full-width charts. Prefill,
  gateway cost, VRAM, and KV-cache comparisons use larger secondary canvases with explicit legends.

## Responsive behavior

- Desktop canvas stays capped near 1500 px and uses reduced outer padding.
- At 760 px and below, controls, KPI cards, and chart groups stack without horizontal overflow.
- Mobile page titles use a 1.85–2.05 rem range; body copy remains 16 px minimum.
- Charts retain at least 320 px height on narrow screens, with readable axis labels and tooltips.

## Non-goals

- No telemetry, routing, evidence, or benchmark calculation changes.
- No new pages, navigation levels, animation system, or decorative illustration.
- No attempt to imitate Grafana or add unsupported operational claims.

## Verification

- Existing dashboard and repository tests remain green.
- Add tests for the new typography floor and reusable chart configuration.
- Perform one bounded visual inspection at desktop and 390 px mobile across all four views.
- Verify no horizontal overflow, no Streamlit exceptions, and no browser console errors attributable
  to the implementation.
