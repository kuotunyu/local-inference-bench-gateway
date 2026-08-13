# Activity Chart Mark Weight Design

## Goal

Increase the visual weight of the Overview activity chart without changing telemetry, aggregation,
scales, ticks, tooltips, colors, or responsive behavior.

## Approved Treatment

- Raise the request Bar desktop maximum from 46 px to 54 px.
- Raise the responsive Bar density multiplier from 0.72 to 0.82. The existing bucket-count-aware
  expression remains in place, so six-hour and 24-hour series still preserve space between buckets.
- Raise the P95 latency line from 4 px to 5 px.
- Raise the P95 point area from 96 to 120 while retaining the existing two-pixel point stroke.
- Preserve the current Morandi green `#5F7F6B` and copper `#B56F45`, opacity, five-minute domain
  padding, adaptive clock-aligned ticks, independent Y scales, chart height, and hover values.

## Responsive and Accessibility Constraints

- Seven-bucket desktop charts should use the full 54 px Bar maximum.
- Narrow or dense charts must continue scaling Bar width from chart width and valid bucket count.
- Marks may become more prominent, but axis labels and grid lines must remain readable.
- No data value, time-window behavior, or evidence semantics may change.

## Verification

- Update Altair-spec tests for the new Bar expression, line width, and point size.
- Retain explicit 37-bucket and 145-bucket coverage.
- Run dashboard and full repository tests, Ruff, and release checks.
- Restart the branch preview and inspect Overview at desktop and 390 px once.
