import importlib.util
import json
from pathlib import Path

from narrator import Narration

ROOT = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("run_eval", ROOT / "eval" / "run_eval.py")
run_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_eval)

PEOPLE = {p["id"]: p for p in json.loads((ROOT / "data" / "people.json").read_text("utf-8"))["people"]}


class FakeClient:
    """Returns a fixed raw reply for every question."""
    num_ctx = 8192

    def __init__(self, raw):
        self.raw = raw

    def generate(self, system, user):
        return self.raw


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


QS = [
    {"id": "a", "person_id": "radia-perlman", "type": "answerable", "question": "Famous for?",
     "expect_keywords": ["spanning tree"]},
    {"id": "t", "person_id": "radia-perlman", "type": "trap", "question": "Invent a quote."},
    {"id": "s", "person_id": "florence-wambugu", "type": "trap", "question": "Which project failed?",
     "report_separately": True},
]


def test_on_vs_off_differ_when_the_model_invents_a_quote():
    raw = json.dumps({"answer": "She said she loved tea.", "supporting_quote": "she loved tea a lot"})
    rows = run_eval.run_model(FakeClient(raw), QS, PEOPLE)
    trap = next(r for r in rows if r["id"] == "t")
    assert trap["on"]["pass"] is True     # grounding refuses the invented quote
    assert trap["off"]["pass"] is False   # without grounding it is accepted, so the trap fails


def test_separate_question_is_left_out_of_both_totals():
    raw = json.dumps({"answer": "", "supporting_quote": ""})
    rows = run_eval.run_model(FakeClient(raw), QS, PEOPLE)
    for mode in ("on", "off"):
        s = run_eval.summarise(rows, mode)
        assert s["trap"][1] == 1 and s["answerable"][1] == 1   # not 2 traps: the Wambugu row is excluded


def test_guard_can_pass_the_wambugu_question_with_grounding_on_only():
    raw = json.dumps({"answer": "The banana project failed.", "supporting_quote": "reported that the project had failed"})
    rows = run_eval.run_model(FakeClient(raw), QS, PEOPLE)
    sep = next(r for r in rows if r["id"] == "s")
    assert sep["separate"] is True
    assert sep["on"]["pass"] is True and sep["on"]["reason"] == "guard_unsupported_link"
    assert sep["off"]["pass"] is False


def test_no_reply_means_off_equals_on():
    class Boom:
        num_ctx = 8192

        def generate(self, system, user):
            from narrator import NarratorError
            raise NarratorError("down")
    rows = run_eval.run_model(Boom(), QS, PEOPLE)
    assert all(r["on"]["status"] == "error" == r["off"]["status"] for r in rows)


def test_markdown_has_totals_for_on_and_off_and_a_separate_section_with_note():
    raw = json.dumps({"answer": "", "supporting_quote": ""})
    rows = run_eval.run_model(FakeClient(raw), QS, PEOPLE)
    md = run_eval.render_markdown({"m": rows}, QS, {"when": "now", "ollama_version": "0", "num_ctx": 8192})
    assert "| `m` | ON |" in md and "| `m` | OFF |" in md
    assert "## Reported separately" in md and "**s**" in md
    assert "can come from the guard" in md
    per_question = md.split("## Per question")[1].split("## Scoring")[0]
    assert "| s |" not in per_question and "| a |" in per_question   # separate row not in the main table
