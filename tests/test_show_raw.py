import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("show_raw", ROOT / "eval" / "show_raw.py")
show_raw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(show_raw)

PEOPLE = {p["id"]: p for p in json.loads((ROOT / "data" / "people.json").read_text("utf-8"))["people"]}
QUESTIONS = json.loads((ROOT / "eval" / "questions.json").read_text("utf-8"))
Q = {q["id"]: q for q in QUESTIONS}


class FakeClient:
    num_ctx = 4096

    def __init__(self, raw):
        self.raw = raw

    def generate(self, system, user):
        return self.raw


def reply(answer, quote):
    return json.dumps({"answer": answer, "supporting_quote": quote})


def test_answer_with_empty_quote_is_refused_on_but_ok_off():
    # Same shape as eval q08 and q09: ON says model_cannot_answer, OFF says ok.
    text = show_raw.describe(Q["q08"], PEOPLE["gladys-west"], reply("She went to a university.", ""))
    assert "supporting_quote is EMPTY" in text
    assert "Grounding ON : status=not_in_sources reason=model_cannot_answer" in text
    assert "Grounding OFF: status=ok" in text


def test_guard_does_not_fire_without_a_listed_word():
    # A reply that mentions "failed" but names no listed word passes the guard.
    raw = reply("New Scientist said the project had failed, but the excerpt does not say which.",
                "the project had failed")
    text = show_raw.describe(Q["q07"], PEOPLE["florence-wambugu"], raw)
    assert "guard does not fire" in text and "forbidden words found []" in text
    assert "Grounding ON : status=ok" in text


def test_guard_fires_when_a_listed_word_is_named():
    raw = reply("The banana project had failed.", "the project had failed")
    text = show_raw.describe(Q["q07"], PEOPLE["florence-wambugu"], raw)
    assert "guard FIRES" in text and "Grounding ON : status=not_in_sources reason=guard_unsupported_link" in text


def test_show_runs_the_same_path_as_the_app_and_prints_the_raw_reply():
    raw = reply("", "")
    out = show_raw.show(["q06", "q10"], FakeClient(raw), PEOPLE, QUESTIONS)
    assert out.count("Raw model reply:") == 2 and raw in out


def test_unknown_id_is_reported_not_raised():
    out = show_raw.show(["q99"], FakeClient("{}"), PEOPLE, QUESTIONS)
    assert out.startswith("Unknown question id(s): q99")


def test_bad_json_does_not_crash():
    out = show_raw.describe(Q["q01"], PEOPLE["radia-perlman"], "not json at all")
    assert "Parsed JSON: none (bad_json)" in out and "status=bad_json" in out
