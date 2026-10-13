# Taiwan knowledge: thinking quality versus local inference cost

Measured 2026-10-13; source commit `4fbe490`. Both arms completed 1,696 questions,
with zero HTTP/runtime errors. Local results, not an official leaderboard entry.
See [fixed protocol](OPENTWBENCH_PROTOCOL.md) for pinned data/model/runtime and scoring.

## Decision for Gateway

**Keep thinking off as the recommended starting configuration for this model on this
workload. Treat bounded thinking as an opt-in tradeoff, not a reliability upgrade.**
No Gateway defaults or routing were changed by this experiment.

Thinking gained 39 net correct answers (+2.30 percentage points), while average
request latency was 4.89 times higher and completion-token use was 4.74 times higher.
This gives Gateway a measured quality/cost dimension alongside its existing engine
performance evidence. It does not justify another model-training project or a default
switch. A future explicit fast/deliberate option would need integration verification;
these measurements called llama.cpp directly, not the Gateway HTTP service.

## Full-run results

| Measurement | Thinking off | Thinking on, budget 512 |
|---|---:|---:|
| Questions | 1,696 | 1,696 |
| Correct | 845 | 884 |
| Accuracy | 49.82% | 52.12% |
| Unparsed (counted incorrect) | 8 | 15 |
| Parse rate | 99.53% | 99.12% |
| Length finishes (not automatically incorrect) | 4 | 8 |
| HTTP/runtime errors | 0 | 0 |
| Mean client latency | 1.388 s | 6.790 s |
| Median client latency | 1.036 s | 6.629 s |
| p95 client latency | 2.962 s | 11.202 s |
| Sum of client request durations | 39.22 min | 191.92 min |
| Completion tokens, total | 199,326 | 945,236 |
| Completion tokens per question | 117.53 | 557.33 |
| Responses with separate reasoning content | 0 | 1,696 |

Completion-token totals use backend `usage`, including reasoning; they are not an
independent tokenizer count or electricity measurement. Summed request durations
exclude startup, warmups and inter-request controller overhead. The two formal stages
ran approximately 18:36–19:16 and 19:16–22:29 Taiwan time.

## Paired result and uncertainty

- Wrong → right: **211**; right → wrong: **172**.
- Both right: 673; both wrong: 640. Total: 1,696.
- Net gain: 39/1,696 = **2.2995 percentage points**.
- Question-paired percentile bootstrap 95% interval: **+0.059 to +4.540 points**
  (20,000 resamples, NumPy default_rng seed 20261013; resample question pairs).
- Exact two-sided discordant-pair binomial test: **p = 0.0520**
  (2 × P[Binomial(383, 0.5) ≤ 172]).

The interval barely clears zero while the discrete exact test does not cross 0.05;
this is marginal evidence, not a robust claim of superiority. These calculations
capture variation across questions, not run-to-run, dataset construction or hardware
uncertainty. There was one off-then-on run, with no counterbalanced repetitions.

Observed incremental request time was 9,161.94 seconds (152.70 minutes): about
234.92 seconds per **net additional correct answer** across this fixed batch.
That ratio is descriptive and unstable when the accuracy difference is near zero;
it is not a prediction of the cost of fixing an individual answer.

## Categories (descriptive only)

| Category | n | Off correct / accuracy | On correct / accuracy | Change (points) |
|---|---:|---:|---:|---:|
| Art | 96 | 40 / 41.67% | 43 / 44.79% | +3.12 |
| Culture | 143 | 71 / 49.65% | 77 / 53.85% | +4.20 |
| Economy | 133 | 65 / 48.87% | 69 / 51.88% | +3.01 |
| Food | 132 | 66 / 50.00% | 71 / 53.79% | +3.79 |
| Geography | 136 | 68 / 50.00% | 72 / 52.94% | +2.94 |
| History | 90 | 55 / 61.11% | 52 / 57.78% | -3.33 |
| Lifestyle | 71 | 32 / 45.07% | 40 / 56.34% | +11.27 |
| Music | 82 | 39 / 47.56% | 41 / 50.00% | +2.44 |
| Nature | 80 | 41 / 51.25% | 37 / 46.25% | -5.00 |
| People | 394 | 198 / 50.25% | 209 / 53.05% | +2.79 |
| Politics | 24 | 11 / 45.83% | 13 / 54.17% | +8.33 |
| Society | 199 | 97 / 48.74% | 99 / 49.75% | +1.01 |
| Technology | 116 | 62 / 53.45% | 61 / 52.59% | -0.86 |

Lifestyle improved most in points, but only has 71 questions. Politics has just 24.
History, Nature and Technology declined. No category-wise significance or automatic
category router is claimed; choosing routing rules from this table would require a
separate held-out evaluation. Do not equate longer answers with better factual knowledge.

## Concrete engineering value

1. **Configuration selection with evidence.** A latency-oriented application can start
   with thinking off; a latency-tolerant caller can consciously opt into more computation.
   This result supports a documented tradeoff, not an unconditional production SLA.
2. **Quality joins performance.** The portfolio can explain why faster token generation
   alone is insufficient, and why a higher score alone does not settle deployment choice.
3. **Protocol validation is part of serving.** Reasoning and final-answer channels must
   remain separate. Synthetic checks demonstrated the distinction, and the evaluator
   now pins `reasoning_format=deepseek` on each request and stops on leaked markers.
4. **Limits drive the next decision.** Roughly half of this local factual MCQ corpus
   remains incorrect. Thinking does not substitute for a verified knowledge source.
   RAG, additional models and training are possible separate hypotheses, not outcomes
   established by this run and not automatically scheduled next steps.

For an interview: “I measured an optional reasoning budget on a pinned local model:
+2.30 points on 1,696 paired Taiwan-knowledge questions cost 4.89× mean latency,
with 172 previously correct answers becoming wrong. I therefore did not blindly
turn on reasoning; I retained a fast starting configuration and documented the
uncertainty and serving-protocol failure that we caught.”

## Audit and excluded work

Recomputed all 3,392 outcomes with unchanged Twinkle Eval 2.10.0 BoxExtractor on
final content only. Verified 13 dataset file hashes, preparation hash, identical
ordered unique IDs/gold/category, prompts, and requests differing only in the
thinking flag. Manifests differ only in thinking flag and start timestamp; every
response reports the pinned runtime fingerprint. Raw checksums:

- off: `8e91b3ef73f667dbd8960821ae74dbb2e5753c853ac4de5beb6156d3dd59a371`
- on: `f55aab73e25a60aa11809a8ccf5adbf3c31b5f16d88934d148872cb1a90fca16`

Prepared input SHA-256:
`f797b01292a15d57c21c8c1ab1cc91cff3cd97eee03af0f9a0b8cb488584ab79`.
Raw questions/responses remain local under the data-license policy; no raw dataset
or machine-specific paths are committed. Local analysis script and aggregate JSON
are retained with the experiment evidence.

Excluded attempts were preserved, not silently replaced:

- Initial wrapper failure: 3 synthetic requests, 0 formal; 4.82 request-seconds.
- Reasoning-channel incident: 1,509 partial off questions plus 3 synthetic requests;
  2,031.90 request-seconds and 178,873 completion tokens. Excluded from all comparisons.
- Incorrect `/props` validation guard: 0 requests. Source inspection showed that this
  runtime serializes fresh task defaults in `/props`; it is not the effective chat
  reasoning setting. That guard was replaced, not weakened to accept mixed content.
- Accepted run: both 3-question synthetic arms passed channel-separation checks
  before the two formal arms. Synthetic accuracy is not part of the benchmark.

Excluded request durations total about 33.95 minutes, excluding model-load/controller
cost. The wrapper-encoding attempt failed before model load. These costs are not
hidden in the valid-arm performance comparison.

The recorded overall GPU-memory snapshots around warmup/formal boundaries were 9,008–9,104 MiB as reported by nvidia-smi; they are
**not peak or model-exclusive memory measurements**. The release snapshot was
1,283 MiB and the owned controller/server had exited. No TTFT was measured.
This is one quantized model, one host, one run order and a factual multiple-choice
corpus. It does not validate Gateway load/failover performance, general Taiwanese
language understanding, agent capability or model-family superiority.

Verification note: evaluator tests pass. An existing unrelated Windows workflow
hung-child timing test intermittently failed during preparation; its deadline and
implementation were not changed, and this report does not claim that failure fixed.
