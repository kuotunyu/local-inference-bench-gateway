# Request Metric Ribbon Design

## Goal

Reduce wasted space in the seven-metric Request summary while preserving every value, readable type,
and the flat scientific-console visual language.

## Approved Direction

Use a compact vertical hierarchy inside each of the seven equal metric cells: label, value, then
supporting detail. The current side-by-side label/value layout is retained for other metric counts;
only `metric-count-7` becomes a compact ribbon.

At desktop widths the seven metrics remain in one row. Below 1180 px they use the existing four-plus-
three grid, and below 760 px they use the existing two-column grid. Labels must not split inside a
word. Values remain the strongest element and supporting detail remains at the approved readable
type size.

## Constraints

- Do not remove, abbreviate, or recompute any metric.
- Do not add cards, shadows, rounded containers, icons, or decorative color.
- Do not reduce the current 17 px desktop supporting-text floor or 15 px mobile floor.
- Preserve the existing flat dividers and responsive grid semantics.

## Verification

- Theme tests assert the seven-card vertical hierarchy, compact height, and no intra-word wrapping.
- Browser inspection confirms the desktop ribbon uses the available width without blank internal
  columns or clipped values.
- Full tests, Ruff, release checks, and the Impeccable detector pass.
