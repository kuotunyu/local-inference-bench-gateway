"""Calibrates long filler prompts to a target prompt_tokens count against a live engine.

Token counts depend on the model's own tokenizer via each engine's usage.prompt_tokens, so a
prompt is calibrated once (against whichever engine is up first) and then reused byte-for-byte
across all three engines -- the parity check (parity.py) then confirms all three report the
same prompt_tokens for that exact text, which is the real proof the calibration transfers.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

# See bench/parity.py for why this is needed on Windows consoles.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass
import yaml

from bench.client import build_messages, stream_chat_completion

# Original filler text (not copied from any external source) themed around local LLM serving,
# repeated/varied to build up length. Deliberately verbose and non-repetitive at the sentence
# level so it behaves like a real long-context prompt rather than degenerate repeated tokens.
_FILLER_SENTENCES = [
    "本地推論引擎在部署大型語言模型時，必須權衡記憶體頻寬、運算吞吐與延遲之間的取捨。",
    "當同一份權重檔案被不同的服務框架載入時，排程策略與批次處理的預設值往往才是效能差異的真正來源。",
    "連續批次處理讓伺服器可以在既有請求仍在生成的同時，動態地把新請求插入運算佇列，藉此提升整體吞吐量。",
    "KV 快取的大小與上下文長度、注意力頭數以及並行請求數量成正比，直接決定了顯示卡記憶體的佔用上限。",
    "在評估首字延遲與生成速度時，暖機執行與多次重複取中位數是避免雜訊干擾量測結果的基本方法。",
    "不同引擎對於預設參數的選擇，例如上下文視窗大小、並行槽位數量與取樣策略，都可能悄悄影響公平比較的前提。",
    "量化技術透過犧牲些許數值精度換取更小的記憶體佔用與更快的讀取速度，是消費級顯示卡上運行大型模型的關鍵手段。",
    "串流回應的分塊格式、結束原因欄位與使用量統計，是實作相容層時最容易出現細節落差的地方。",
    "健康檢查與容錯移轉機制讓服務在單一後端故障時仍能維持可用性，這對正式環境的穩定性至關重要。",
    "效能數字高度依賴硬體、驅動程式版本與作業系統排程行為，任何橫向評測都應該誠實揭露測試環境的細節。",
]


def build_filler_text(approx_chars: int) -> str:
    parts: list[str] = []
    total = 0
    i = 0
    while total < approx_chars:
        s = _FILLER_SENTENCES[i % len(_FILLER_SENTENCES)]
        parts.append(f"({i + 1}) {s}")
        total += len(s)
        i += 1
    return " ".join(parts)


async def _measure_prompt_tokens(
    base_url: str, model: str, api_key: str | None, system_prompt: str, text: str
) -> int:
    messages = build_messages(system_prompt, text)
    async with httpx.AsyncClient() as client:
        result = await stream_chat_completion(
            client,
            base_url,
            model,
            messages,
            api_key=api_key,
            max_tokens=1,
            engine_label="calibration",
        )
    if result.success and result.prompt_tokens is not None:
        return result.prompt_tokens

    # The server's context window is deliberately smaller than the largest calibration probe
    # (binary search starts from a generous upper bound) -- an "exceeds context size" rejection
    # still reports the real token count it tried to process, so use that instead of crashing.
    if result.error:
        try:
            error_body = json.loads(result.error)
            n_prompt_tokens = error_body.get("error", {}).get("n_prompt_tokens")
            if n_prompt_tokens is not None:
                return int(n_prompt_tokens)
        except json.JSONDecodeError:
            pass

    raise RuntimeError(f"calibration request failed: {result.error}")


async def calibrate_prompt(
    base_url: str,
    model: str,
    api_key: str | None,
    system_prompt: str,
    target_tokens: int,
    tolerance_pct: float = 2.0,
    max_iterations: int = 12,
) -> tuple[str, int]:
    """Binary-search the filler text length until prompt_tokens is within tolerance of target."""
    tolerance = target_tokens * tolerance_pct / 100.0

    # Chinese text in this corpus runs roughly ~1.6-2 chars/token; start from that estimate.
    lo_chars, hi_chars = 1, target_tokens * 4
    best_text, best_tokens = "", 0

    for _ in range(max_iterations):
        mid_chars = (lo_chars + hi_chars) // 2
        text = build_filler_text(mid_chars)
        tokens = await _measure_prompt_tokens(base_url, model, api_key, system_prompt, text)
        best_text, best_tokens = text, tokens

        if abs(tokens - target_tokens) <= tolerance:
            return text, tokens
        if tokens < target_tokens:
            lo_chars = mid_chars + 1
        else:
            hi_chars = mid_chars - 1
        if lo_chars >= hi_chars:
            break

    return best_text, best_tokens


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="bench/config.yaml")
    parser.add_argument("--reference-engine", default="llamacpp")
    args = parser.parse_args()

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    engine_cfg = config["engines"][args.reference_engine]
    out_dir = Path(config["paths"]["calibrated_prompts_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    for target in config["prompt_token_targets"]:
        print(f"Calibrating prompt for target={target} tokens against {args.reference_engine} ...")
        text, actual = await calibrate_prompt(
            engine_cfg["base_url"],
            engine_cfg["model"],
            engine_cfg.get("api_key"),
            config["system_prompt"],
            target,
            tolerance_pct=config["prompt_tolerance_pct"],
        )
        deviation_pct = abs(actual - target) / target * 100
        print(f"  -> actual prompt_tokens={actual} (target {target}, deviation {deviation_pct:.2f}%)")

        out_path = out_dir / f"prompt_{target}.json"
        out_path.write_text(
            json.dumps(
                {
                    "target_tokens": target,
                    "actual_tokens": actual,
                    "reference_engine": args.reference_engine,
                    "text": text,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"  saved -> {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
