"""Show the raw model reply for chosen eval questions, and how it is judged.

Usage (from the repo root, with Ollama running):
    python eval/show_raw.py q07 q08 q09

The model is the one the app uses (OLLAMA_MODEL, or the default tag).
Nothing is written to disk and results.md is not touched.

Why this exists: eval/run_eval.py keeps each raw reply only long enough to score
it, so results.md has verdicts but not the model's JSON. This script makes a NEW
call with the same prompt and settings. Even at temperature 0 a new call may not
repeat the saved eval reply word for word, so treat it as a fresh sample.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from grounding import parse_model_json, quote_in_excerpt  # noqa: E402
from narrator import DEFAULT_NUM_CTX, OllamaClient, answer_question, narration_from_raw  # noqa: E402

DATA_FILE = ROOT / "data" / "people.json"
QUESTIONS_FILE = ROOT / "eval" / "questions.json"


class _Recorder:
    """Wraps a model client and remembers the last raw reply."""

    def __init__(self, client):
        self.client = client
        self.num_ctx = getattr(client, "num_ctx", DEFAULT_NUM_CTX)
        self.raw = None

    def generate(self, system, user):
        self.raw = None
        self.raw = self.client.generate(system, user)
        return self.raw


def guard_detail(answer: str, guards) -> list[str]:
    """For each guard: which trigger words and which forbidden words the answer contains."""
    low = (answer or "").lower()
    out = []
    for g in guards or []:
        when = [w for w in g.get("when_answer_contains", []) if w.lower() in low]
        banned = [w for w in g.get("must_not_contain", []) if w.lower() in low]
        fires = bool(when) and bool(banned)
        out.append(f"guard {'FIRES' if fires else 'does not fire'}: trigger words found {when}, "
                   f"forbidden words found {banned} (it needs one of each)")
    return out


def describe(question: dict, person: dict, raw) -> str:
    """Plain-text report for one question and one raw reply."""
    lines = [f"=== {question['id']} ({question['type']}) {person['name']}",
             f"Question: {question['question']}", "", "Raw model reply:", str(raw), ""]
    data = parse_model_json(raw) if raw is not None else None
    excerpt = (person.get("sources") or [{}])[0].get("excerpt", "")
    answer = quote = None
    if data is None:
        lines.append("Parsed JSON: none (bad_json)")
    else:
        answer, quote = data.get("answer"), data.get("supporting_quote")
        lines += [f"answer:           {answer!r}", f"supporting_quote: {quote!r}"]
        if isinstance(quote, str) and quote.strip():
            lines.append(f"quote found word for word in one passage of the excerpt: "
                         f"{quote_in_excerpt(quote, excerpt)}")
        elif isinstance(quote, str):
            lines.append("supporting_quote is EMPTY. With grounding ON an empty quote is refused "
                         "(reason empty_quote); with grounding OFF only the answer is checked.")
        if not isinstance(answer, str) or not answer.strip():
            lines.append("answer is EMPTY or missing. Both modes refuse it (reason empty_answer).")
    lines += guard_detail(answer if isinstance(answer, str) else "", person.get("guards"))
    for label, grounded in (("ON ", True), ("OFF", False)):
        n = narration_from_raw(raw, person, grounded=grounded) if raw is not None else None
        if n is None:
            lines.append(f"Grounding {label}: no reply")
            continue
        lines.append(f"Grounding {label}: status={n.status} reason={n.reason or '-'} text={n.text!r}")
    return "\n".join(lines)


def show(ids, client, people: dict, questions: list) -> str:
    by_id = {q["id"]: q for q in questions}
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        return f"Unknown question id(s): {', '.join(unknown)}. Known: {', '.join(sorted(by_id))}"
    parts = []
    for qid in ids:
        q = by_id[qid]
        person = people[q["person_id"]]
        rec = _Recorder(client)
        on = answer_question(rec, person, q["question"], num_ctx=rec.num_ctx)
        if rec.raw is None:  # the model was not reached, or the prompt was too long
            parts.append(f"=== {qid}: no raw reply. status={on.status} reason={on.reason} text={on.text}")
        else:
            parts.append(describe(q, person, rec.raw))
    return "\n\n".join(parts)


def main(argv) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # names like Wambugu print safely on Windows
    ids = [a for a in argv[1:] if not a.startswith("-")]
    if not ids:
        print("Usage: python eval/show_raw.py q07 q08 q09")
        return 2
    people = {p["id"]: p for p in json.loads(DATA_FILE.read_text("utf-8"))["people"]}
    questions = json.loads(QUESTIONS_FILE.read_text("utf-8"))
    client = OllamaClient()
    print(f"Model: {client.model}  num_ctx: {client.num_ctx}  (a new call, not the saved eval reply)\n")
    text = show(ids, client, people, questions)
    print(text)
    return 2 if text.startswith("Unknown question id") else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
