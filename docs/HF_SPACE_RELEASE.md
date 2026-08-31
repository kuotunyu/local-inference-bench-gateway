# Hugging Face Space release runbook

This runbook is for a future, separately authorized release of exactly
`steven0226/local-inference-bench-gateway`. It is not deployment authorization. Execute each gate
in order and stop on every ambiguous, nonzero, or incomplete result. Do not add a Space URL to the
repository README. No SLA is offered or implied.

Paths containing `NEVER_DEPLOY` are prohibited inputs to every remote command. The disposable
`NEVER_DEPLOY-hf-space-tampered` fixture described below is local-only and must never be created in,
uploaded to, or otherwise passed to Hugging Face, GitHub, or another remote service.

## 1. Frozen local validation and clean export

Run the complete local gate from the repository root:

```powershell
uv sync --frozen --all-extras
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen pytest -q -p no:cacheprovider
uv run --frozen python -m release_checks.cli
$dirty = git status --porcelain
if ($dirty) { throw "Release export requires a clean HEAD: $dirty" }
$reviewRoot = New-Item -ItemType Directory -Path (Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString()))
$bundle = Join-Path $reviewRoot.FullName 'hf-space'
uv run --frozen python scripts/export_hf_space.py --destination $bundle
```

Before the export, verify that `$reviewRoot` is a newly created GUID-named directory directly under
the operating-system temp directory and that `$bundle` is its nonexistent child. Abort if the
child already exists, the source HEAD is dirty, or the deployment manifest does not name the exact
source commit. Run `verify_space_bundle(Path.cwd(), Path($bundle))` and require no violations.

Confirm that the bundle includes the scoped `LICENSE`, `THIRD_PARTY_NOTICES.md`, source revision
manifest, all 12 declared evidence artifacts, `provenance.json`, and `claims.json`. Confirm its card
and runtime state that free/default compute may sleep and cold-start and does not promise always-on
availability.

## 2. Local valid-bundle visual review

Build and run the reviewed bundle locally with a unique task-owned image, container, and loopback
port. Do not expose the port beyond `127.0.0.1`. At exact `1440x900` and `390x844` viewports, visit
all four views:

1. `Demo 概覽`
2. `Demo Routing 與可靠性`
3. `Demo Request 紀錄`
4. `Committed Benchmark Evidence`

On every fresh session, require this exact truth contract before the first interactive control:

```text
公開證據示範（Demo Mode）
此 Space 僅呈現 deterministic illustrative fixture 與 2026-07-17 committed aggregate evidence。它不會、也無法連線到訪客的本機 Gateway、SQLite、inference backend 或 GPU；不是 live inference service，亦無 SLA。Space 可能休眠或 cold-start；其啟動狀態不代表 Gateway uptime。
Deterministic Demo data is illustrative and is not production or sampled traffic.
Benchmark evidence is a dated, hardware- and version-specific snapshot.
Request-level raw benchmark runs are not public.
This Space cannot connect to a visitor's local system.
This Space provides neither live inference nor an SLA.
Hosting sleep or cold start is not system uptime evidence.
```

For both viewports, record each of these visual and claim checks:

- The truth contract is visible before the first control without scrolling.
- `document.documentElement.scrollWidth === document.documentElement.clientWidth` evaluates to
  `true`; navigation, charts, legends, tooltips, table columns, and disclosures are readable.
- The persistent `DETERMINISTIC DEMO · 非正式流量` badge identifies the three Demo views, and the
  evidence view shows `COMMITTED EVIDENCE · aggregate only · raw runs unpublished`.
- No endpoint URL, local URL, health endpoint, prompt input, file upload, or gateway configuration
  appears. No Demo/Live selector or live refresh control appears.
- No current model or GPU execution claim, current queue/backend-health claim, universal engine
  winner claim, production-readiness claim, uptime claim, or SLA claim appears.
- The evidence view reports `12/12 verified artifacts`. No degraded-evidence warning appears.
- Zero browser-console errors and zero Streamlit exceptions are present.
- The scoped `LICENSE` and `THIRD_PARTY_NOTICES.md` links are present and readable.
- The Space sleep/cold-start disclosure is present and does not describe Gateway uptime.

For each viewport, capture an unintercepted CDP or Playwright request graph while visiting all four
views. Preserve the original full URL, resource type, and initiator metadata for every request
outside the allowed boundary. Only loopback and same-origin runtime requests are permitted. Require
exactly zero external origins. Any external origin, including `data.streamlit.io` and Fivetran, is
RED. Do not block, abort, intercept, rewrite, or fulfill requests to make this gate pass. Preserve
the graph evidence and stop if the boundary is violated.

Retain screenshots only under ignored `.dashboard-cache/space-visual/valid/`. Remove the exact
valid-review container after inspection, but retain the reviewed bundle until the tamper gate below
finishes.

## 3. Local fail-closed NEVER_DEPLOY review

Copy the already verified valid bundle to a newly created GUID-named temp root whose child is named
exactly `NEVER_DEPLOY-hf-space-tampered`. Add a sibling `NEVER_DEPLOY.txt` warning. Alter only
`bench/results/gateway_overhead.json` by appending one LF byte with no encoding rewrite. Require the
bundle verifier to return exactly one `evidence byte mismatch` violation.

Build and run that disposable copy locally using a unique `never-deploy` image, container, and
loopback port. Inspect only `Committed Benchmark Evidence` at exact `1440x900` and `390x844`:

- `Unavailable — evidence integrity check failed` is visible for the affected panel.
- The canonical `Gateway median TTFT overhead: 1.66 ms` value is suppressed.
- Independently verified, unaffected panels remain readable.
- Zero browser-console errors and zero Streamlit exceptions are present.

For each viewport, capture an unintercepted CDP or Playwright request graph while reviewing the
tampered evidence view. Preserve the original full URL, resource type, and initiator metadata for
every request outside the allowed boundary. Only loopback and same-origin runtime requests are
permitted. Require exactly zero external origins. Any external origin, including
`data.streamlit.io` and Fivetran, is RED. Do not block, abort, intercept, rewrite, or fulfill
requests to make this gate pass. Preserve the graph evidence and stop if the boundary is violated.

Retain screenshots only under ignored `.dashboard-cache/space-visual/NEVER_DEPLOY/`. Remove the
exact disposable container, then resolve and validate both task-owned roots before recursive
cleanup: each root must be an immediate child of the operating-system temp directory and its leaf
must parse as a `D`-format GUID. Remove only those validated roots. Never upload the tampered bundle,
image, container, marker, or screenshots.

## 4. Authenticated collision preflight

Only a future operator who has owner credentials and explicit authority may run this real remote
gate, after every local gate above and immediately before the creation authorization stop:

```powershell
uv run --frozen python -m release_checks.space_remote_gate
```

The preflight performs GET only. It verifies the exact owner, Docker eligibility, exact-ID absence,
and a complete collision-free namespace listing. Implementation agents never execute it without
owner credentials and authority. Any existing object, collision, authentication failure, rate
limit, timeout, incomplete pagination, malformed response, or ambiguous result is a hard stop.

## STOP — separate owner authorization required for Space creation

Do not continue without a new, explicit owner approval for remote Space creation and upload. The
approved valid bundle must still be byte-identical to the locally reviewed bundle, its source HEAD
must still be approved, and its resolved path must not contain `NEVER_DEPLOY`. A create-time
conflict stops the release; never delete, overwrite, rename, repurpose, transfer, or destructively
retry against an existing Space.

After that approval only, the first write-capable remote operation creates the exact new public
Docker Space; the immediately following operation uploads the exact reviewed bundle:

```powershell
uv run --with huggingface_hub python -c "from huggingface_hub import HfApi; HfApi().create_repo(repo_id='steven0226/local-inference-bench-gateway', repo_type='space', space_sdk='docker', private=False, exist_ok=False)"
uv run --with huggingface_hub python -c "import sys; from huggingface_hub import HfApi; HfApi().upload_folder(repo_id='steven0226/local-inference-bench-gateway', repo_type='space', folder_path=sys.argv[1])" $bundle
```

## 5. Public Space cold-start and mobile/desktop review

Verify the canonical Hub page reports the intended source identity, public and not-disabled state,
Space commit, and matching GitHub source revision. Let free/default compute sleep, then verify a
cold start and repeat all four-view checks at exact `1440x900` and `390x844`. Recheck the truth
contract, claim ceiling, `12/12` evidence status, absence of degraded warnings, scoped license,
notices and documentation links, browser console, Streamlit exceptions, runtime logs, horizontal
overflow, and absence of endpoint, Live, model/GPU-current-execution, uptime, or SLA claims.

Record the reviewed Space commit and source revision in the portfolio control ledger. A planned,
building, private, disabled, broken, or unreviewed Space is never eligible for GitHub About.

## STOP — separate owner authorization required for GitHub About

A successful deployment does not authorize an About edit. Request and obtain separate explicit
owner approval before the following GitHub mutation. The only approved value is the canonical Hub
page, never a runtime `*.hf.space` subdomain:

`https://huggingface.co/spaces/steven0226/local-inference-bench-gateway`

After that separate approval only, set and then read back the exact value:

```powershell
$canonicalHubUrl = 'https://huggingface.co/spaces/steven0226/local-inference-bench-gateway'
gh api --method PATCH repos/kuotunyu/local-inference-bench-gateway -f homepage="$canonicalHubUrl"
gh api --method GET repos/kuotunyu/local-inference-bench-gateway --jq .homepage
```

Require the final API readback to equal `$canonicalHubUrl` exactly. Stop on any mismatch; do not
substitute another URL or mutate the repository README.
