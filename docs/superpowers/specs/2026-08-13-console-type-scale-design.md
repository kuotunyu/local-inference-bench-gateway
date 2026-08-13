# Console Type Scale Design

## Goal

Increase every undersized text role by 2–4 px without inflating page titles, weakening hierarchy,
or reintroducing wasted space and wrapping defects.

## Approved Type Scale

- Body and control text remain at the established 18 px desktop baseline.
- Supporting UI text moves from 17 px to 19 px: source notes, metric labels/details, status details,
  callout copy, chart keys, captions, and inline technical code.
- Dense data text moves from 15 px to 17 px: DataFrame headers and cells.
- Chart axes and legends move from 15–16 px to 18 px.
- Mobile body text moves from 16 px to 18 px; mobile supporting text moves from 15 px to 17 px.
- Display headings and large metric values remain unchanged so hierarchy does not flatten.

## Layout Protection

The seven-metric Request ribbon keeps its vertical label/value/detail hierarchy. Its label tracking
and horizontal padding may be tightened without reducing font size, and the four-plus-three layout
must begin early enough to prevent overflow after the label increase. Other metric counts retain
their current responsive structure.

## Verification

- Theme and chart tests assert the new role floors.
- Browser review covers Request records, Benchmark evidence, chart labels, DataFrame cells, and the
  responsive metric ribbon at wide and ordinary widths.
- No horizontal overflow, clipped label, or word-by-word wrapping is permitted.
- Full tests, Ruff, release checks, and the Impeccable type detector must pass.
