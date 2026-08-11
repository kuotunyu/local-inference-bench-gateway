# Setup

## CPU-only reviewer setup

Requirements: Git, Python 3.12–3.14, and [uv](https://docs.astral.sh/uv/). No GPU, model, inference
engine, or Docker daemon is required for the static evidence and unit-test path.

```bash
uv sync --frozen --all-extras
uv run --frozen pytest -q
uv run --frozen python -m release_checks.cli
```

The checks use mocked HTTP backends and temporary SQLite databases. They do not contact the engine
URLs in `gateway/models.yaml`.

## Native gateway

Copy the safe template and choose a long random local key:

```powershell
Copy-Item .env.example .env
uv sync --frozen --extra dev
uv run uvicorn gateway.app:app --host 127.0.0.1 --port 9000
```

Relevant environment variables:

| Variable | Purpose | Default |
|---|---|---|
| `GATEWAY_API_KEY` | Enables Bearer authentication when non-empty | authentication disabled |
| `GATEWAY_MODELS_PATH` | Path to an alias/backend registry | `gateway/models.yaml` |
| `GATEWAY_DB_PATH` | Local SQLite telemetry path | `data/gateway.db` |

Edit `gateway/models.yaml` to point at OpenAI-compatible backends that you separately install and
operate. Use only loopback addresses unless you also add transport security and network policy.

Health and API examples:

```powershell
Invoke-RestMethod http://127.0.0.1:9000/health
$headers = @{ Authorization = "Bearer $env:GATEWAY_API_KEY" }
Invoke-RestMethod http://127.0.0.1:9000/v1/models -Headers $headers
```

## Dashboard

The dashboard reads the same SQLite file and should remain loopback-only:

```bash
uv sync --frozen --extra dashboard
uv run streamlit run dashboard/app.py --server.address 127.0.0.1
```

## Docker

The normal Compose file runs only the gateway and dashboard. It expects separately managed host
inference services and binds published ports to `127.0.0.1`. The smoke Compose file is CPU-only and
uses deterministic mock backends. Run these commands from the repository root—the directory that
contains `Dockerfile` and `compose.smoke.yaml`:

```bash
docker compose up --build
docker compose -f compose.smoke.yaml up --build --abort-on-container-exit --exit-code-from smoke-client
docker compose -f compose.smoke.yaml down --volumes --remove-orphans
```

## Optional GPU benchmark reproduction

This section is intentionally separate from the reviewer path. It is manual, machine-specific,
and can consume substantial disk, VRAM, and time.

1. Obtain `Ministral-3-8B-Instruct-2512-Q4_K_M.gguf` from its publisher and verify the exact size
   and SHA-256 in `bench/results/provenance.json`. Do not commit it.
2. Install the recorded or deliberately chosen versions of llama.cpp, Ollama, and LM Studio from
   their official sources. Record any deviation before comparing results.
3. Configure one engine at a time with the same model, prompt template, context allocation,
   sampling values, and OpenAI-compatible endpoint. Verify prompt-token parity before timing.
4. Confirm only the measured engine is resident on the GPU and that the system is not spilling to
   host memory.
5. Run `python -m bench.runner` only after reading `bench/config.yaml`; it writes request-level raw
   output to an ignored directory. Never publish that output without a separate privacy review.
6. Run `python -m bench.analyze` to produce summaries in a staging location. Do not overwrite the
   committed evidence unless intentionally creating a new, fully reviewed benchmark release.

The committed evidence remains the 2026-07-17 run. A reproduction on different hardware or newer
software is a new experiment, not a validation that should silently replace it.
