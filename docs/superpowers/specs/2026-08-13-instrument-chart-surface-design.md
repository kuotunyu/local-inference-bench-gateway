# Instrument Chart & Flat Surface Design

## Objective

Refine the Operations Console so the primary activity chart reads as a deliberate scientific
instrument and the surrounding interface no longer relies on a rounded card for every content
group. Preserve all telemetry meaning, four-view navigation, large chart canvases, and the current
Traditional Chinese / original technical term language convention.

## Approved direction: Flat Scientific Instrument

Use one clear chart focal point and a flatter surface hierarchy. Borders, backgrounds, and rounded
corners remain only when they communicate interaction, state, or a scrollable data boundary.

## Activity chart

### Time domain and outer breathing room

- Keep the existing 10-minute aggregation buckets and all underlying values unchanged.
- Extend the rendered temporal domain by five minutes before the first bucket and five minutes
  after the last bucket. This equals half one bucket and prevents the first and last bars from
  touching the plot boundary.
- Apply the same explicit temporal domain to both the request-volume bars and P95-latency line.
- Drop invalid timestamps before deriving the domain. If fewer than two valid timestamps remain,
  use a five-minute fallback on each side of the available timestamp.

### Tick interval

- Target approximately seven labeled X-axis ticks across the plot.
- Select the smallest interval from this fixed sequence that is at least `span / 6`:
  `10 min`, `30 min`, `1 h`, `2 h`, `4 h`, `6 h`, `12 h`, `1 d`, `2 d`, `7 d`.
- Align ticks to clock boundaries by rounding the first tick upward to the selected interval and
  generate values through the final timestamp.
- This yields 10-minute ticks for the 60-minute view, 1-hour ticks for the 6-hour view, and 4-hour
  ticks for the 24-hour view.
- Render visible 6 px tick marks with a stronger neutral axis color. Keep labels horizontal and use
  greedy label-overlap handling on narrow screens; tick marks remain meaningful even when some
  labels are omitted.

### Marks and color

- Increase bar width from 34 px to 46 px.
- Use `#5F7F6B` for bars at 0.90 opacity. This is a darker, clearer extension of the approved
  Morandi green.
- Increase the P95 line from 3 px to 4 px.
- Use `#B56F45` for the line and points, with 96 px filled points and a 2 px stroke.
- Retain independent Y scales, the 400 px chart height, existing tooltips, and the dual-axis titles.
- Keep grid lines light; strengthen only axes, ticks, and data marks.

## Surface hierarchy

### Remove card-everywhere styling

- Convert the KPI area into one instrument rail with a top and bottom hairline. Individual metrics
  use vertical separators, transparent backgrounds, square corners, and no shadows.
- On mobile, preserve the two-column KPI layout. Use row and column separators instead of restoring
  rounded cards.
- Convert `.status-card` usages in Backend Health and Routing into flat rows separated by a bottom
  hairline. Keep status dots because their shape communicates health.
- Remove the navigation group's outer border, rounded container, and panel background. The active
  navigation item uses a restrained bottom indicator and a subtle tint without a pill shape.

### Keep boundaries where they carry meaning

- Keep source badges as pills because they are compact state labels.
- Keep a visible boundary around Streamlit inputs and buttons; reduce their radius to 6 px.
- Keep data-frame and expander boundaries because they define scrollable or collapsible regions;
  reduce their radius to 4 px.
- Keep callout backgrounds and semantic border colors for warnings, failures, empty states, and
  degraded states; reduce callout radius to 4 px.
- Do not add new wrappers, shadows, animations, icons, or decorative chart containers.

## Responsive behavior

- Desktop and wide layouts retain five KPI metrics in one rail.
- At 760 px and below, KPI metrics remain two columns with separator logic adjusted for row breaks.
- The temporal plot remains horizontally contained at 390 px; greedy overlap may suppress some X
  labels but must not create horizontal page overflow.
- All retained controls keep usable touch targets and visible focus states.

## Data and behavior boundaries

- No changes to request slicing, SQLite reads, aggregation frequency, metric calculations, routing,
  failover, health probes, Benchmark evidence, or provenance verification.
- No changes to chart height, observation-window options, filters, tables, or navigation behavior.
- Missing data continues to render as unavailable rather than zero.

## Verification

- Add deterministic tests for five-minute domain padding, 10-minute ticks in the 60-minute fixture,
  thicker marks, stronger colors, and synchronized X encodings across both layers.
- Update theme tests for the flat KPI rail, flat status rows, borderless navigation group, and the
  reduced radii that remain.
- Run dashboard tests, the full repository suite, Ruff lint/format, and all release checks.
- Inspect all four views at desktop and 390 px mobile in one bounded browser pass, followed by at
  most one batched correction and one confirmation pass.
- Verify no horizontal overflow, no Streamlit exceptions, and no new browser-console errors.

## Non-goals

- No visual-world replacement, dark theme, sidebar, chart animation, new metrics, or dashboard
  framework migration.
- No removal of boundaries that communicate input affordance, data scrolling, disclosure, or
  operational state.
