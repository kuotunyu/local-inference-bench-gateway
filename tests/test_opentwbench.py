import pytest

from bench.opentwbench import prepare_rows, score_response, summarize


def row(**extra):
    return dict(
        question="Choose",
        A="one",
        B="two",
        C="three",
        D="four",
        answer="B",
        category="test",
        context="SECRET GOLD CONTEXT",
        **extra,
    )


def test_prepare_is_stable_and_keeps_gold_out_of_prompt():
    first = prepare_rows([row()], seed=42)[0]
    assert prepare_rows([row()], seed=42) == [first]
    assert "SECRET" not in first["prompt"]
    assert first["options"][first["answer"]] == "two"
    assert set(first) == {"id", "category", "prompt", "options", "answer"}


def test_reject_duplicates_and_invalid_gold():
    with pytest.raises(ValueError):
        prepare_rows([row(), row()], seed=42)
    invalid = row()
    invalid["answer"] = "E"
    with pytest.raises(ValueError):
        prepare_rows([invalid], seed=42)


def test_missing_final_answer_does_not_score_thinking():
    response = {
        "choices": [
            {
                "finish_reason": "length",
                "message": {"content": None, "reasoning_content": r"\boxed{B}"},
            }
        ]
    }
    result = score_response(response, "B", lambda text: "B" if text else None)
    assert result["correct"] is False
    assert result["parsed"] is False
    assert result["finish_reason"] == "length"


def test_failures_stay_in_denominator():
    records = [
        {"correct": True, "parsed": True, "error": None},
        {"correct": False, "parsed": False, "error": "timeout"},
    ]
    result = summarize(records)
    assert result["accuracy"] == 0.5
    assert result["parse_rate"] == 0.5
    assert result["errors"] == 1


def test_out_of_range_and_truncated_answers_are_visible():
    response = {"choices": [{"finish_reason": "length", "message": {"content": "x"}}]}
    assert not score_response(response, "B", lambda _: "Z")["parsed"]
    result = score_response(response, "B", lambda _: "B")
    assert result["correct"]
    assert result["finish_reason"] == "length"


@pytest.fixture
def fake_eval_backend(monkeypatch):
    """Exercise admission and persistence without a model or optional installation."""
    import importlib.metadata
    import sys
    import types

    import httpx

    from bench import opentwbench

    module_name = "twinkle_eval.metrics.extractors.box"
    fake_module = types.ModuleType(module_name)

    class FakeExtractor:
        def extract(self, content):
            return content if content in {"A", "B", "C", "D"} else None

    fake_module.BoxExtractor = FakeExtractor
    monkeypatch.setitem(sys.modules, module_name, fake_module)
    real_version = importlib.metadata.version
    monkeypatch.setattr(
        importlib.metadata,
        "version",
        lambda name: "2.10.0" if name == "twinkle-eval" else real_version(name),
    )
    real_client = httpx.Client

    def install(handler):
        monkeypatch.setattr(
            opentwbench.httpx,
            "Client",
            lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
        )

    return install


def run_args(tmp_path):
    import argparse
    import json

    dataset = tmp_path / "dataset"
    dataset.mkdir()
    second = row()
    second["question"] = "Another question"
    (dataset / "test.jsonl").write_text(
        "\n".join(json.dumps(item) for item in [row(), second]), encoding="utf-8"
    )
    return argparse.Namespace(
        dataset=dataset,
        output=tmp_path / "output",
        revision="synthetic",
        expected_count=2,
        seed=42,
        model_sha256="0" * 64,
        base_url="http://127.0.0.1:18765",
        thinking=False,
    )


def test_http_failure_preserved_and_no_next_question(tmp_path, fake_eval_backend):
    import json

    import httpx

    from bench.opentwbench import run

    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/props":
            return httpx.Response(
                200,
                json={"default_generation_settings": {"params": {"reasoning_format": "deepseek"}}},
            )
        return httpx.Response(503, json={"error": "synthetic failure"})

    fake_eval_backend(handler)
    args = run_args(tmp_path)
    with pytest.raises(RuntimeError, match="failed or incomplete"):
        run(args)
    raw = [
        json.loads(line)
        for line in (args.output / "raw.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    summary = json.loads((args.output / "summary.json").read_text(encoding="utf-8"))
    assert calls == ["/props", "/v1/chat/completions"]
    assert len(raw) == 1 and raw[0]["http_status"] == 503
    assert raw[0]["error"].startswith("HTTPStatusError")
    assert summary["complete"] is False and summary["expected"] == 2
    assert summary["errors"] == 1 and summary["requests"] == 1


def test_existing_output_never_overwritten_or_sent(tmp_path, fake_eval_backend):
    from bench.opentwbench import run

    def forbidden(_):
        pytest.fail("No backend calls permitted for an existing output directory")

    fake_eval_backend(forbidden)
    args = run_args(tmp_path)
    args.output.mkdir()
    sentinel = args.output / "raw.jsonl"
    sentinel.write_bytes(b"preserved evidence")
    with pytest.raises(FileExistsError):
        run(args)
    assert sentinel.read_bytes() == b"preserved evidence"


def test_unparsed_response_does_not_abort_or_leak_context(tmp_path, fake_eval_backend):
    import json

    import httpx

    from bench.opentwbench import run

    submitted = []

    def handler(request):
        if request.url.path == "/props":
            return httpx.Response(
                200,
                json={"default_generation_settings": {"params": {"reasoning_format": "deepseek"}}},
            )
        submitted.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={"choices": [{"finish_reason": "length", "message": {"content": "unparseable"}}]},
        )

    fake_eval_backend(handler)
    args = run_args(tmp_path)
    run(args)
    summary = json.loads((args.output / "summary.json").read_text(encoding="utf-8"))
    assert len(submitted) == 2 and "SECRET" not in json.dumps(submitted)
    assert summary["complete"] is True and summary["errors"] == 0
    assert summary["accuracy"] == 0 and summary["parse_rate"] == 0
    assert summary["length_finishes"] == 2


@pytest.mark.parametrize("mode", ["none", "deepseek-legacy", None])
def test_reasoning_protocol_rejected_before_questions(tmp_path, fake_eval_backend, mode):
    import json

    import httpx

    from bench.opentwbench import run

    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/props":
            return httpx.Response(
                200, json={"default_generation_settings": {"params": {"reasoning_format": mode}}}
            )
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "A"}, "finish_reason": "stop"}]}
        )

    fake_eval_backend(handler)
    args = run_args(tmp_path)
    with pytest.raises(ValueError, match="reasoning-format deepseek"):
        run(args)
    assert calls == ["/props"]
    assert not (args.output / "raw.jsonl").exists()
    manifest = json.loads((args.output / "manifest.json").read_text(encoding="utf-8"))
    assert (
        manifest["server_props"]["default_generation_settings"]["params"]["reasoning_format"]
        == mode
    )
