# Taiwan knowledge and local inference cost

Status: preparation and synthetic smoke only; no Formosa benchmark scores yet.
This is a new, independent experiment. Earlier engine benchmarks remain frozen.

## Question and fixed configurations

Does a bounded thinking mode improve Taiwan knowledge accuracy enough to justify its
additional local inference time? Compare **one model**, Gemma 4 12B IT QAT Q4_0,
with `enable_thinking=false` versus `enable_thinking=true`. The llama.cpp server's
thinking budget is 512 tokens. This is a deployment-configuration comparison, not a
model-family comparison or a quantization ablation.

- Model: `google/gemma-4-12B-it-qat-q4_0-gguf`, revision
  `29d097773436b69ff9feafd636ab4cf873786537`.
- GGUF SHA-256: `93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b`.
- Runtime: llama.cpp build 10964, commit `b29c606e2`; native Windows CUDA.
- One RTX 4090, one server slot, full GPU offload, context 4096, flash attention on,
  automatic fitting off, eight CPU threads. No image projector is needed.
- Temperature 0, top-p 1, seed 42, output cap 1536 tokens for both configurations,
  no prompt cache reuse, no retry, one outstanding request.

## Dataset and scoring

Use all 1,696 rows in the 13 category files of
[OpenTWBench/tw-formosa-bench](https://huggingface.co/datasets/OpenTWBench/tw-formosa-bench)
at revision `5e9dd9cea085640ffd1ec7d2708446c820cbb39e`. Record each file hash.
Do not also concatenate the `all` view: it represents the same questions.

Only the question and A–D options enter the prompt. Never send `context`, the gold
answer, or source article text. Shuffle options deterministically per question hash
and seed, remap the gold answer, and use the identical prepared questions for both modes.
Repeated stems with the same unordered option set fail preparation.

Use the unchanged `BoxExtractor` from `twinkle-eval==2.10.0`, but apply it only to
final `message.content`. Start the server with `--reasoning-format deepseek` so
thoughts are separated into `reasoning_content`. Each request also explicitly sets
`reasoning_format=deepseek`; synthetic warmups must demonstrate separate reasoning
before formal admission. The evaluator stops on leaked channel markers rather than
extracting an intermediate answer. In this pinned runtime, `/props` serializes a
fresh task's defaults, so its `reasoning_format` is not the effective chat setting
([source](https://github.com/ggml-org/llama.cpp/blob/b29c606e2/tools/server/server-context.cpp)).
Preserve it for provenance, but verify actual responses. Unlike that version's standard runner, do not fall back to
reasoning when final content is absent. Preserve finish reason, including truncation.
Parsed answers outside A–D are invalid. Unparsed answers remain incorrect in the
denominator; report their rate separately. A parsed answer on a length finish is scored
normally, but truncation count must remain visible.

Infrastructure errors are saved and stop the run. Partial runs are not full benchmark
results. Do not overwrite output directories, silently retry failed requests, change
the parser, or select prompts based on formal scores. Resume/restart requires an
explicit incident decision and retains the failed attempt.

## Measurement and interpretation

Retain raw request/response, usage, backend timings and client end-to-end seconds.
Warm up on synthetic questions outside this dataset before each arm. Run the two arms
sequentially with the same settings; do not compare congested or thermally different
runs as a pure thinking-mode effect. This non-streaming path does **not** measure TTFT.
Record model-resident and observed GPU memory separately from weights-on-disk size.
Windows WDDM overall VRAM includes desktop applications, so do not label it isolated
model VRAM. Latency results describe this host/runtime, not a universal speed claim.

The final report must include completeness, micro accuracy, category counts/accuracy,
parse and truncation rates, paired correct/incorrect transitions and paired bootstrap
uncertainty, token use and latency distributions. Separate successful responses from
infrastructure failures without hiding the latter. No automatic winner selection.

This is **not** a reproduction of the official full-precision leaderboard: weights,
prompt, inference budget, shuffle and final-only scoring are our declared local protocol.
Dataset knowledge and factual quality follow the source corpus; this does not establish
general Taiwanese language ability, RAG reliability, agent ability or clinical validity.

## Reproduction entry point

Install the optional evaluator into a separate environment with
`pip install twinkle-eval==2.10.0`. Keep the Gateway environment and lockfile unchanged.
Download the 13 category JSONL files from the pinned dataset revision into a local data
directory. Start the pinned local server with the settings above, then run from repo root:

```text
python -m bench.opentwbench --dataset DATASET_DIRECTORY --revision 5e9dd9cea085640ffd1ec7d2708446c820cbb39e --expected-count 1696 --model-sha256 93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b --output NEW_OUTPUT_DIRECTORY
```

Add `--thinking` for the second arm and choose a different, new output directory.
Model hash is declared provenance in this CLI; the operator must verify the actual
served GGUF before launch. The run also saves `/props`, including the served template.

Dataset content is CC BY-SA 4.0, derived from Taiwan.md. Preserve attribution and its
license on any redistributed source questions/derived dataset. Dataset files and raw
runs remain local; this repository's MIT code license does not replace the data license.
Twinkle Eval is MIT licensed: https://github.com/ai-twinkle/Eval.
