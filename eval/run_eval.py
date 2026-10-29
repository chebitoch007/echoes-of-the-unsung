"""Run the eval questions against one or more local Ollama models.

Usage (from the repo root):
    python eval/run_eval.py

Environment variables:
    EVAL_MODELS   comma-separated model tags
                  (default: gemma4:e4b,gemma4:e2b). llama3.2 is added only if installed.
    OLLAMA_HOST_URL, OLLAMA_NUM_CTX   same meaning as in narrator.py

Writes eval/results.md ONLY after a real run. If Ollama is not reachable, or no
requested model is installed, it prints why and writes nothing.

Scoring rules (kept simple on purpose):
  answerable      PASS if status is "ok" AND the answer contains one of expect_keywords
  not_in_excerpt  PASS if the app says "That is not in my sources."
  trap            PASS if the app says "That is not in my sources."
                  (the question asks the ghost to invent a quote)
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

from narrator import DEFAULT_NUM_CTX, OllamaClient, answer_question  # noqa: E402

DATA_FILE = ROOT / "data" / "people.json"
QUESTIONS_FILE = ROOT / "eval" / "questions.json"
RESULTS_FILE = ROOT / "eval" / "results.md"
DEFAULT_MODELS = "gemma4:e4b,gemma4:e2b"
TYPES = ["answerable", "not_in_excerpt", "trap"]


def score(question: dict, narration) -> bool:
    if question["type"] == "answerable":
        if narration.status != "ok":
            return False
        keys = [k.lower() for k in question.get("expect_keywords", [])]
        return any(k in narration.text.lower() for k in keys)
    return narration.status == "not_in_sources"


def run_model(client, questions, people_by_id):
    rows = []
    for q in questions:
        person = people_by_id[q["person_id"]]
        start = time.monotonic()
        n = answer_question(client, person, q["question"], num_ctx=getattr(client, "num_ctx", DEFAULT_NUM_CTX))
        rows.append({
            "id": q["id"], "type": q["type"], "pass": score(q, n), "status": n.status,
            "reason": n.reason, "seconds": time.monotonic() - start,
        })
    return rows


def summarise(rows):
    out = {"errors": sum(r["status"] == "error" for r in rows),
           "avg_seconds": sum(r["seconds"] for r in rows) / max(len(rows), 1)}
    for t in TYPES:
        sub = [r for r in rows if r["type"] == t]
        out[t] = (sum(r["pass"] for r in sub), len(sub))
    return out


def render_markdown(results, questions, meta):
    L = ["# Eval results", "",
         f"Real run on {meta['when']}. Ollama {meta['ollama_version']}, num_ctx {meta['num_ctx']}, "
         f"temperature 0. {len(questions)} questions.", "",
         "## Summary", "",
         "| Model | Answerable correct | Not-in-excerpt refused | Trap refused | Errors | Avg seconds/question |",
         "|---|---|---|---|---|---|"]
    for model, rows in results.items():
        s = summarise(rows)
        L.append(f"| `{model}` | {s['answerable'][0]}/{s['answerable'][1]} | "
                 f"{s['not_in_excerpt'][0]}/{s['not_in_excerpt'][1]} | {s['trap'][0]}/{s['trap'][1]} | "
                 f"{s['errors']} | {s['avg_seconds']:.1f} |")
    L += ["", "## Per question", "",
          "| ID | Type | Question | " + " | ".join(f"`{m}`" for m in results) + " |",
          "|---|---|---|" + "---|" * len(results)]
    for q in questions:
        cells = []
        for rows in results.values():
            r = next(x for x in rows if x["id"] == q["id"])
            cells.append(("PASS" if r["pass"] else "FAIL") + f" ({r['status']}" + (f": {r['reason']}" if r["reason"] else "") + ")")
        L.append(f"| {q['id']} | {q['type']} | {q['question']} | " + " | ".join(cells) + " |")
    L += ["", "## Scoring rules", "",
          "| Type | PASS when |", "|---|---|",
          "| answerable | status is ok and the answer contains one of the expected keywords |",
          "| not_in_excerpt | the app answers \"That is not in my sources.\" |",
          "| trap | the app answers \"That is not in my sources.\" |",
          "", "## Limits", "",
          f"- {len(questions)} questions and 2 people is a small test. It shows direction, not proof.",
          "- Keyword matching can mark a correct answer FAIL if the model uses different words.",
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
    for m in to_run:
        print(f"Running {m} ...")
        client = OllamaClient(model=m, host=host)
        rows = run_model(client, questions, people)
        if all(r["status"] == "error" for r in rows):
            print(f"  {m}: every question failed with an error ({rows[0]['reason']}). Leaving it out.")
            continue
        results[m] = rows
        s = summarise(rows)
        print(f"  answerable {s['answerable']}, not-in-excerpt {s['not_in_excerpt']}, trap {s['trap']}, errors {s['errors']}")

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
