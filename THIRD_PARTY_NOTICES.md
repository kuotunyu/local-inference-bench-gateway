# Third-party notices and license boundaries

This repository does not redistribute model weights or inference-engine binaries. The root
`LICENSE` applies only to original source code authored by kuotunyu.

## Recorded benchmark model

The recorded benchmark used
[`mistralai/Ministral-3-8B-Instruct-2512-GGUF`](https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512-GGUF),
which its publisher identifies as Apache License 2.0. Model files are excluded from this
repository. Anyone who downloads a model must review and comply with the model's current license
and usage terms.

## Inference engines

- [llama.cpp](https://github.com/ggml-org/llama.cpp) is not redistributed here. Its upstream
  repository publishes an MIT license.
- [Ollama](https://github.com/ollama/ollama) is not redistributed here. Its open-source upstream
  repository publishes an MIT license; separately distributed applications may have different
  terms.
- [LM Studio Desktop](https://lmstudio.ai/app-terms) is not redistributed or licensed by this
  project. It is governed by Element Labs' app terms. The separately published `lms` CLI has its
  own upstream license.

## Python dependencies

Python packages are resolved from `uv.lock` and remain under their respective upstream licenses.
The lockfile is dependency metadata, not a relicensing of those packages. Installed package
metadata is the authoritative source for the exact resolved version's license notices.

Trademarks and product names belong to their respective owners. References identify the systems
used in the recorded experiment and do not imply endorsement.
