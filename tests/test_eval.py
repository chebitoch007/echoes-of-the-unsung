import importlib.util
from pathlib import Path

from narrator import Narration

spec = importlib.util.spec_from_file_location(
    "run_eval", Path(__file__).parent.parent / "eval" / "run_eval.py")
run_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_eval)


def test_answerable_needs_ok_and_keyword():
    q = {"type": "answerable", "expect_keywords": ["widget"]}
    assert run_eval.score(q, Narration("ok", text="She built a Widget."))
    assert not run_eval.score(q, Narration("ok", text="She built a gadget."))
    assert not run_eval.score(q, Narration("not_in_sources"))


def test_refusal_types_need_not_in_sources():
    for t in ("not_in_excerpt", "trap"):
        assert run_eval.score({"type": t}, Narration("not_in_sources"))
        assert not run_eval.score({"type": t}, Narration("ok", text="x"))
        assert not run_eval.score({"type": t}, Narration("error", text="x"))


def test_summary_and_markdown_with_fake_rows():
    qs = [{"id": "q1", "type": "answerable", "question": "Q?", "person_id": "p"}]
    rows = [{"id": "q1", "type": "answerable", "pass": True, "status": "ok", "reason": "", "seconds": 2.0}]
    s = run_eval.summarise(rows)
    assert s["answerable"] == (1, 1) and s["errors"] == 0
    md = run_eval.render_markdown({"m": rows}, qs, {"when": "now", "ollama_version": "0", "num_ctx": 8192})
    assert "| `m` | 1/1 |" in md and "PASS (ok)" in md
