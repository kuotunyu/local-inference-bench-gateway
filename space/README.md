---
title: Local Inference Benchmark Gateway · Public Evidence Demo
emoji: "◉"
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
license: mit
---

# Local Inference Benchmark Gateway · Public Evidence Demo

公開證據示範（Demo Mode）

此 Space 僅呈現 deterministic illustrative fixture 與 2026-07-17 committed aggregate evidence。它不會、也無法連線到訪客的本機 Gateway、SQLite、inference backend 或 GPU；不是 live inference service，亦無 SLA。Space 可能休眠或 cold-start；其啟動狀態不代表 Gateway uptime。

Deterministic Demo data is illustrative and is not production or sampled traffic.

Benchmark evidence is a dated, hardware- and version-specific snapshot.

Request-level raw benchmark runs are not public.

This Space cannot connect to a visitor's local system.

This Space provides neither live inference nor an SLA.

Hosting sleep or cold start is not system uptime evidence.

## What this Space contains

This CPU-only Docker Space renders four public-safe views: a deterministic Demo Overview, Demo
Routing and Reliability, Demo Request Records, and Committed Benchmark Evidence. Demo records are
immutable in-memory illustrative fixture data. Benchmark evidence is read-only committed aggregate
artifacts verified by their provenance and claims manifests.

The public boundary is **aggregate only · raw runs unpublished**. Request-level raw benchmark runs
are not distributed or regenerated here, and the evidence snapshot is not a universal engine
ranking, current GPU execution claim, uptime measurement, or service-level guarantee.

The application does not accept prompts, uploads, credentials, backend addresses, database paths, or
inference parameters. It performs no server-side network access to a visitor's machine, a Gateway,
an inference engine, model repository, or remote API. The internal health check only checks the
container-local Streamlit process at `http://127.0.0.1:7860/_stcore/health`.

## Recorded evidence

The committed benchmark snapshot was measured on 2026-07-17 with an NVIDIA GeForce RTX 4090 and a
recorded model/version configuration. It is hardware-, version-, and workload-specific evidence.
The Space presents aggregate throughput, TTFT, prefill, gateway-overhead, VRAM, and controlled
Unified KV Cache comparisons where the corresponding committed artifacts verify successfully.

## Source and license boundaries

The canonical source repository is
[`kuotunyu/local-inference-bench-gateway`](https://github.com/kuotunyu/local-inference-bench-gateway).
The scoped [MIT License](LICENSE) applies only to original source code authored by kuotunyu;
third-party models, engines, packages, trademarks, and benchmark facts retain their own terms.
See the [Third-party notices](THIRD_PARTY_NOTICES.md) for the recorded model and dependency
license boundaries.

## Hosting lifecycle

Free or default hosting may sleep when idle and may require a cold start. Hosting sleep or
cold-start behavior is a property of the Space host; it is not evidence of Gateway uptime,
availability, or an SLA. No paid always-on hardware or availability guarantee is implied.
