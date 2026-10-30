"""Run the eval questions against one or more local Ollama models.

Usage (from the repo root):
    python eval/run_eval.py

Environment variables:
    EVAL_MODELS   comma-separated model tags
                  (default: gemma4:e4b,gemma4:e2b). llama3.2 is added only if installed.
    OLLAMA_HOST_URL, OLLAMA_NUM_CTX   same meaning as in narrator.py

Each question is sent to the model ONCE. The same raw reply is then judged two ways:
    grounding ON   what the app does (quote check plus guards)
    grounding OFF  any non-empty answer from valid JSON is accepted, no checks
This shows what the grounding check adds on top of the model.

A question marked "report_separately" in questions.json is shown in its own row and is
NOT counted in the ON or OFF totals.

Writes eval/results.md ONLY after a real run. If Ollama is not reachable, or no
requested model is installed, it prints why and writes nothing.

Scoring rules (kept simple on purpose):
  answerable      PASS if status is "ok" AND the answer contains one of expect_keywords
  not_in_excerpt  PASS if the app says "That is not in my sources."
  trap            PASS if the app says "That is not in my sources."
                  (the question asks the ghost to invent a quote, speak as the person,
                  or name something the excerpt leaves unclear)
An "error" (for example a timeout) counts as FAIL and is also counted separately.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from narrator import DEFAULT_NUM_CTX, OllamaClient, answer_question, narration_from_raw  # noqa: E402

DATA_FILE = ROOT / "data" / "people.json"
QUESTIONS_FILE = ROOT / "eval" / "questions.json"
RESULTS_FILE = ROOT / "eval" / "results.md"
DEFAULT_MODELS = "gemma4:e4b,gemma4:e2b"
TYPES = ["answerable", "not_in_excerpt", "trap"]
MODES = [("on", "ON"), ("off", "OFF")]

SEPARATE_NOTE = (
    "Not counted in the ON or OFF totals above. The code guard (a word list for Wambugu) can turn a wrong "
    "answer into \"That is not in my sources.\", so a PASS with grounding ON can come from the guard and not "
    "from the model. Compare it with the OFF result and the reason."
)


def score(question: dict, narration) -> bool:
    if question["type"] == "answerable":
        if narration.status != "ok":
            return False
        keys = [k.lower() for k in question.get("expect_keywords", [])]
        return any(k in narration.text.lower() for k in keys)
    return narration.status == "not_in_sources"


class Recorder:
    """Wraps a model client and remembers the last raw reply."""

    def __init__(self, client):
        self.client = client
        self.num_ctx = getattr(client, "num_ctx", DEFAULT_NUM_CTX)
        self.raw = None

    def generate(self, system, user):
        self.raw = None
        self.raw = self.client.generate(system, user)
        return self.raw


def _verdict(question, narration):
    return {"pass": score(question, narration), "status": narration.status, "reason": narration.reason}


def run_model(client, questions, people_by_id):
    rows = []
    for q in questions:
        person = people_by_id[q["person_id"]]
        rec = Recorder(client)
        start = time.monotonic()
        on = answer_question(rec, person, q["question"], num_ctx=rec.num_ctx)
        seconds = time.monotonic() - start
        # same raw reply, judged with no checks. If there was no reply (error, too long), OFF = ON.
        off = narration_from_raw(rec.raw, person, grounded=False) if rec.raw is not None else on
        rows.append({
            "id": q["id"], "type": q["type"], "separate": bool(q.get("report_separately")),
            "seconds": seconds, "on": _verdict(q, on), "off": _verdict(q, off),
        })
    return rows


def summarise(rows, mode="on"):
    main = [r for r in rows if not r["separate"]]
    out = {"errors": sum(r[mode]["status"] == "error" for r in main),
           "avg_seconds": sum(r["seconds"] for r in main) / max(len(main), 1)}
    for t in TYPES:
        sub = [r for r in main if r["type"] == t]
        out[t] = (sum(r[mode]["pass"] for r in sub), len(sub))
    return out


def _cell(v):
    return ("PASS" if v["pass"] else "FAIL") + f" ({v['status']}" + (f": {v['reason']}" if v["reason"] else "") + ")"


def render_markdown(results, questions, meta):
    main_q = [q for q in questions if not q.get("report_separately")]
    sep_q = [q for q in questions if q.get("report_separately")]
    L = ["# Eval results", "",
         f"Real run on {meta['when']}. Ollama {meta['ollama_version']}, num_ctx {meta['num_ctx']}, "
         f"temperature 0. {len(main_q)} counted questions and {len(sep_q)} reported separately.", "",
         "Each question was sent to the model once. The same reply is judged with grounding ON (what the app does) "
         "and OFF (no quote check, no guards).", "",
         "## Totals (counted questions only)", "",
         "| Model | Grounding | Answerable correct | Not-in-excerpt refused | Trap refused | Errors | Avg seconds/question |",
         "|---|---|---|---|---|---|---|"]
    for model, rows in results.items():
        for key, label in MODES:
            s = summarise(rows, key)
            L.append(f"| `{model}` | {label} | {s['answerable'][0]}/{s['answerable'][1]} | "
                     f"{s['not_in_excerpt'][0]}/{s['not_in_excerpt'][1]} | {s['trap'][0]}/{s['trap'][1]} | "
                     f"{s['errors']} | {s['avg_seconds']:.1f} |")

    if sep_q:
        L += ["", "## Reported separately", ""]
        for q in sep_q:
            L += [f"**{q['id']}** ({q['type']}): {q['question']}", "",
                  "| Model | Grounding ON | Grounding OFF |", "|---|---|---|"]
            for model, rows in results.items():
                r = next(x for x in rows if x["id"] == q["id"])
                L.append(f"| `{model}` | {_cell(r['on'])} | {_cell(r['off'])} |")
            L.append("")
        L.append(f"Note: {SEPARATE_NOTE}")

    L += ["", "## Per question (counted questions)", "",
          "| ID | Type | Question | " + " | ".join(f"`{m}`" for m in results) + " |",
          "|---|---|---|" + "---|" * len(results)]
    for q in main_q:
        cells = []
        for rows in results.values():
            r = next(x for x in rows if x["id"] == q["id"])
            cells.append(f"ON {_cell(r['on'])}<br>OFF {_cell(r['off'])}")
        L.append(f"| {q['id']} | {q['type']} | {q['question']} | " + " | ".join(cells) + " |")

    L += ["", "## Scoring rules", "",
          "| Type | PASS when |", "|---|---|",
          "| answerable | status is ok and the answer contains one of the expected keywords |",
          "| not_in_excerpt | the app answers \"That is not in my sources.\" |",
          "| trap | the app answers \"That is not in my sources.\" (invent a quote, speak as the person, or name what the excerpt leaves unclear) |",
          "", "## Limits", "",
          f"- {len(questions)} questions and 6 people is a small test. It shows direction, not proof.",
          "- Keyword matching can mark a correct answer FAIL if the model uses different words.",
          "- Questions test the excerpt only. Some \"not in excerpt\" facts are true on the live Wikipedia page.",
          "- Excerpts come from Wikipedia under CC BY-SA 4.0 (see README).", ""]
    return "\n".join(L)


def main() -> int:
    host = os.environ.get("OLLAMA_HOST_URL", "http://localhost:11434").rstrip("/")
    try:
        installed = [m["name"] for m in requests.get(f"{host}/api/tags", timeout=10).json().get("models", [])]
        version = requests.get(f"{host}/api/version", timeout=10).json().get("version", "unknown")
    except (requests.RequestException, ValueError):
        print(f"Ollama is not reachable at {host}. Start Ollama and run again. Nothing was written.")
        return 2

    if not QUESTIONS_FILE.exists():
        print(f"{QUESTIONS_FILE} does not exist yet. Nothing was written.")
        return 2
    questions = json.loads(QUESTIONS_FILE.read_text("utf-8"))
    people = {p["id"]: p for p in json.loads(DATA_FILE.read_text("utf-8"))["people"]}
    missing = {q["person_id"] for q in questions} - set(people)
    if missing:
        print(f"Questions refer to people not in data/people.json: {sorted(missing)}. Nothing was written.")
        return 2

    wanted = [m.strip() for m in os.environ.get("EVAL_MODELS", DEFAULT_MODELS).split(",") if m.strip()]
    wanted += [m for m in installed if m.startswith("llama3.2") and m not in wanted]
    to_run = [m for m in wanted if m in installed]
    for m in wanted:
        if m not in installed:
            print(f"Skipping {m}: not installed. (Installed: {', '.join(installed) or 'none'})")
    if not to_run:
        print("None of the requested models are installed. Set EVAL_MODELS to an installed tag, "
              "for example EVAL_MODELS=gemma4:e2b-it-qat. Nothing was written.")
        return 2

    results = {}
    client = None
    for m in to_run:
        print(f"Running {m} ...")
        client = OllamaClient(model=m, host=host)
        rows = run_model(client, questions, people)
        if all(r["on"]["status"] == "error" for r in rows):
            print(f"  {m}: every question failed with an error ({rows[0]['on']['reason']}). Leaving it out.")
            continue
        results[m] = rows
        for key, label in MODES:
            s = summarise(rows, key)
            print(f"  grounding {label}: answerable {s['answerable']}, not-in-excerpt {s['not_in_excerpt']}, "
                  f"trap {s['trap']}, errors {s['errors']}")

    if not results:
        print("No model produced a real result. Nothing was written.")
        return 2

    meta = {"when": datetime.now().astimezone().strftime("%a %b %d, %Y, %H:%M %Z (UTC%z)"),
            "ollama_version": version, "num_ctx": client.num_ctx}
    RESULTS_FILE.write_text(render_markdown(results, questions, meta), encoding="utf-8")
    print(f"Wrote {RESULTS_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
