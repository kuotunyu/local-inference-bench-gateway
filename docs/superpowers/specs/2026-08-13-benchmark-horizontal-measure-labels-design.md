# Benchmark Horizontal Measure Labels Design

## Goal

Remove every rotated quantitative Y-axis title from the `Benchmark 證據` page and use the same
horizontal measure-label pattern already approved for the Overview chart. Numeric Y-axis ticks,
measurement scales, series legends, and exact-value tooltips remain unchanged.

## Options Considered

### A. Horizontal measure label above each plot — approved

Place one compact, left-aligned label between each chart heading and plot. A line or bar swatch
matches the chart's mark type. This preserves a direct unit-to-plot relationship without requiring
the user to tilt their head.

### B. Put the unit in each section heading

This removes vertical text with less markup, but makes already descriptive headings longer and
mixes the chart's subject with its measurement scale.

### C. Move the unit into the caption below the chart

This is visually quiet but forces users to look below the plot before interpreting the Y-axis
numbers. It weakens scanability and is therefore rejected.

## Scope

The horizontal labels are:

| Chart | Mark cue | Horizontal measure label |
|---|---|---|
| Aggregate decode throughput | line | `Throughput／tok/s` |
| P50 / P95 TTFT by concurrency | line | `TTFT／ms` |
| Prefill calibrated prompt | bar | `Median TTFT／s` |
| Gateway cost | bar | `Latency／ms` |
| VRAM baseline | bar | `VRAM baseline／MiB` |
| Unified KV Cache control | line | `P50 TTFT／ms` |

This scope intentionally covers all quantitative charts on the page so the reading model does not
change halfway through the evidence report.

## Component Design

Promote the existing Overview-only measure key into a small shared HTML component. The component
accepts one or two static label definitions, escapes label text, allows only the known `bar` and
`line` mark types and semantic color tones, and renders decorative swatches with
`aria-hidden="true"`.

- A one-item key stays left aligned for Benchmark charts.
- A two-item key retains the Overview chart's left/right alignment.
- The row remains flat: no border, radius, background panel, or shadow.
- At mobile widths, text remains at least 15 px and items may wrap without causing horizontal
  overflow.

## Chart Semantics

Each Benchmark chart builder passes `y_title=None`. This only removes the rendered axis title.
The following remain byte-for-byte equivalent where practical:

- data frames and derived values;
- X and Y fields;
- zero baselines and domains;
- chart heights;
- engine/series color legends;
- mark widths, points, and colors;
- tooltip fields and captions.

The measure label supplements, rather than replaces, the engine or series legend. For example,
`Throughput／tok/s` explains the Y-axis scale while the existing legend still maps each colored
line to LM Studio, Ollama, or llama.cpp.

## Empty and Degraded States

Render a horizontal label only when its corresponding chart is rendered. Missing or invalid
Artifact states continue to show their existing warning instead, avoiding an orphaned unit label
above an absent plot.

## Verification

- Chart-spec tests assert `encoding.y.title is None` for all six Benchmark charts and preserve the
  expected data fields, legends, heights, and zero-baseline behavior.
- Component tests cover one-item and two-item keys, escaping, allowed mark types, and accessible
  decorative swatches.
- Rendered evidence tests assert all six horizontal labels appear with valid committed fixtures and
  do not appear for missing Artifact states.
- Browser review confirms the Benchmark page has no rotated quantitative axis titles, horizontal
  overflow, clipping, or Streamlit exceptions at the available handoff viewport.
- Full tests, Ruff, release checks, and the Impeccable detector pass before handoff.
