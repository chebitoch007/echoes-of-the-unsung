"""Grounding check: no second AI call.

The model must return JSON: {"answer": "...", "supporting_quote": "..."}.
We accept an answer only if supporting_quote appears word for word in the
excerpt (extra spaces and letter case are ignored).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

NOT_IN_SOURCES = "That is not in my sources."

# A quote shorter than this is too easy to match by luck (for example "the").
MIN_QUOTE_WORDS = 3

# Text inside double quotes in the answer (straight or curly quotes).
_QUOTED_TEXT = re.compile(r'["\u201c]([^"\u201d]+)["\u201d]')
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_CODE_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def normalise(text: str) -> str:
    """Lower-case and collapse all runs of whitespace to one space."""
    return " ".join(text.split()).lower()


_PASSAGE_BREAK = re.compile(r"\n\s*\n")


def quote_in_excerpt(quote: str, excerpt: str) -> bool:
    """True if quote appears word for word in excerpt (spaces and case ignored).

    The excerpt may join passages from different parts of a page with a blank
    line. A quote must sit inside ONE passage, so it cannot glue the end of one
    passage to the start of the next.
    """
    q = normalise(quote)
    if len(q.split()) < MIN_QUOTE_WORDS:
        return False
    return any(q in normalise(passage) for passage in _PASSAGE_BREAK.split(excerpt))


def parse_model_json(raw: str) -> Optional[dict]:
    """Pull the first JSON object out of the model text. Never raises.

    Only the final JSON is used: <think>...</think> blocks and code fences are
    removed first, and any text around the object is ignored.
    """
    if not isinstance(raw, str):
        return None
    text = _THINK_BLOCK.sub("", raw).strip()
    text = _CODE_FENCE.sub("", text).strip()
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
        except ValueError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


@dataclass
class GroundingResult:
    ok: bool
    answer: str = ""
    quote: str = ""
    reason: str = ""  # why it was rejected (for logs and the eval), not shown to users


def violates_guard(answer: str, guards: Optional[list]) -> Optional[str]:
    """Return the guard's reason if the answer fills a gap the excerpt leaves open.

    A guard is {"when_answer_contains": [...], "must_not_contain": [...], "why": "..."}.
    It trips when the answer has any 'when' word AND any 'must_not' word.
    """
    low = answer.lower()
    for g in guards or []:
        if any(w.lower() in low for w in g.get("when_answer_contains", [])) and \
           any(w.lower() in low for w in g.get("must_not_contain", [])):
            return g.get("why", "guard")
    return None


def check_answer(raw_model_output: str, excerpt: str, guards: Optional[list] = None) -> GroundingResult:
    """Decide whether the model output may be shown to the user."""
    data = parse_model_json(raw_model_output)
    if data is None:
        return GroundingResult(False, reason="bad_json")

    answer = data.get("answer")
    quote = data.get("supporting_quote")
    if not isinstance(answer, str) or not isinstance(quote, str):
        return GroundingResult(False, reason="wrong_fields")
    answer, quote = answer.strip(), quote.strip()

    if not answer or not quote:
        return GroundingResult(False, reason="model_cannot_answer")
    if not quote_in_excerpt(quote, excerpt):
        return GroundingResult(False, reason="quote_not_in_excerpt")

    # Extra guard against invented quotes: any quoted words inside the answer
    # must themselves come from the excerpt.
    for inner in _QUOTED_TEXT.findall(answer):
        if len(inner.split()) >= MIN_QUOTE_WORDS and not quote_in_excerpt(inner, excerpt):
            return GroundingResult(False, reason="invented_quote_in_answer")

    if violates_guard(answer, guards):
        return GroundingResult(False, reason="guard_unsupported_link")

    return GroundingResult(True, answer=answer, quote=quote)
