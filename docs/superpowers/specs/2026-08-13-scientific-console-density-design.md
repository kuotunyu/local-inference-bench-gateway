# Scientific Console Density Design

## Objective

Refine the existing Operations Console into a rational, scientific operating surface. The change
must remove editorial-sounding headlines, increase the practical reading size of secondary text,
and use wide-screen space more deliberately without reducing chart area or changing data
semantics.

## Approved direction: Scientific Instrument Layout

Preserve the current restrained Morandi palette, four-view navigation, and evidence-first product
identity. Recompose the top of each page as an instrument panel: compact controls, neutral technical
headings, dense scan-first metrics, and large data canvases.

### Technical copy

Replace editorial headlines with neutral view names:

- **Overview:** `推論閘道運行概覽`
- **Routing & Reliability:** `路由與可靠性分析`
- **Requests:** `請求遙測檢視`
- **Benchmark Evidence:** `Benchmark 測量證據`

Each lede states the data scope and relationship being shown. It must avoid advertising language,
rhetorical punctuation, and unsupported claims. Traditional Chinese remains primary; technical
terms such as request, latency, routing, failover, Backend Health, and Benchmark remain in their
original form when that is clearer.

### Typography floor

- Use an 18 px desktop root and body size.
- Keep desktop page titles in a restrained 1.75--2.05 rem range rather than an editorial hero scale.
- Use 17 px for source notes, KPI labels and details, captions, callout copy, status metadata, and
  control labels.
- Use at least 15 px for chart tick labels and legends, and 16 px for chart axis titles.
- Preserve tabular numerals and strong contrast for KPI values.
- Keep the mobile root at 16 px and do not allow supporting text below 15 px.

### Header composition

- Replace the split brand/controls structure that leaves a blank block above `Operations Console`.
- Give the brand block two useful lines: product name and a short technical descriptor, aligned to
  the control stack.
- Keep Telemetry source, Observation window, and refresh in the same desktop row, but constrain
  their proportions so short values do not sit inside unnecessarily wide fields.
- Reduce shell top padding and the gap between controls, navigation, and page heading.
- Preserve Streamlit-native controls and keyboard behavior.

### Page heading composition

- Render the technical title and explanatory lede in a two-column desktop grid so both sides of the
  canvas carry information.
- Use a 38/62 title-to-description ratio with a modest gap and baseline alignment.
- Stack title and lede at 860 px and below.
- Keep the source badge and observation evidence immediately below the heading, without an extra
  decorative layer.

### KPI composition

- Change metric cards from fixed-height vertical stacks to a compact two-column internal grid.
- Place label and detail on the left; place the primary value on the right, spanning both rows.
- Reduce desktop card minimum height from 108 px to 88 px.
- Keep all five Overview metrics in one desktop row when space permits.
- At narrow widths, return each card to a readable stacked composition and retain the existing
  two-column mobile card grid.
- Missing values remain an em dash and are never converted to zero.

### Charts and downstream content

- Preserve the current enlarged chart canvases; this refinement must not shrink them.
- Increase chart label sizing to the typography floor where necessary.
- Tighten only transitions and wrappers that do not aid comprehension.
- Avoid adding cards around charts or introducing a sidebar, dashboard chrome, animation, or
  decorative visualizations.

## Data and behavior boundaries

- No changes to telemetry loading, SQLite semantics, observation-window calculations, routing,
  failover, Benchmark evidence, or provenance verification.
- No new API calls, pages, filters, or navigation levels.
- Existing Demo/Live state, last-good snapshot behavior, empty states, and degraded states remain
  intact.

## Responsive behavior

- Desktop: use the available wide canvas with compact vertical rhythm and one-row Overview KPIs.
- Tablet: stack the page heading and permit controls to wrap through Streamlit's responsive column
  behavior without overflow.
- Mobile at 760 px and below: keep 16 px body copy, stacked KPI internals, two cards per row where
  legible, and one card per row only when the viewport cannot sustain two.
- All views must remain free of horizontal overflow at 390 px.

## Verification

- Add or update tests for the 18 px desktop base, supporting-text floor, scientific view titles,
  two-column heading markup, and compact KPI grid styling.
- Run the dashboard test suite, full repository tests, Ruff lint/format, and release checks.
- Inspect all four views at desktop width and 390 px mobile in one bounded visual pass.
- Confirm no browser console errors, no Streamlit exceptions, no horizontal overflow, and no
  regression in chart readability.

## Non-goals

- No visual-world replacement, sidebar redesign, Grafana imitation, or new data product.
- No change to the approved Morandi palette.
- No promotional copy or portfolio-only claims inside the operational interface.
