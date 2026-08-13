# Horizontal Chart Axis Labels Design

## Goal

Remove the need to read rotated Y-axis titles in the Overview activity chart while preserving the
dual-axis comparison, scale integrity, and direct association between each measure and its mark.

## Approved Direction

Use a horizontal measure key immediately above the plot area:

- left: a green bar swatch followed by `Request 數量／bucket`;
- right: an orange line swatch followed by `P95 latency／ms`.

The left and right Y axes keep their numeric ticks in their current positions. Both axis titles are
set to `null`, so no vertical text remains. The green and orange labels match the chart marks and
provide a redundant shape cue, ensuring that meaning does not depend on color alone.

## Layout and Hierarchy

The existing section heading `Request 數量與 P95 latency` remains the primary chart title. The new
measure key is a compact secondary row between that heading and the chart. It spans the same width
as the plot, aligns its left item with the left scale and its right item with the right scale, and
does not introduce a bordered card or rounded container.

At narrow widths the row remains horizontal while allowing each label to wrap within its half. The
labels use the existing readable supporting-text size; they must not shrink below the dashboard's
mobile type floor.

## Data and Interaction

No metric, domain, bucket, scale, tooltip, mark width, line weight, or observation-window behavior
changes. Hover continues to expose exact values. The explanatory caption remains and continues to
state that independent Y axes preserve the true magnitudes.

## Accessibility

The visible text names both measures and units. A bar-shaped swatch identifies Request volume and a
line-shaped swatch identifies P95 latency, so users who cannot distinguish the colors still have a
shape-based mapping. The chart specification itself retains tooltip titles for both series.

## Verification

- Chart-spec tests assert that both Y-axis titles are absent while numeric axes remain left/right.
- A rendered AppTest asserts that both horizontal measure labels are visible.
- Browser review covers the current handoff width and a 390 px mobile viewport, checking for
  horizontal overflow, clipping, awkward wrapping, and rendered exceptions.
- Full tests, Ruff, release checks, and the Impeccable detector must pass before handoff.

## Scope

This change applies only to the Overview dual-axis activity chart. Other charts are unchanged
because they do not currently require the user to read paired vertical axis titles.
