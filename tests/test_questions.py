"""Checks that the eval questions are fair against the real data."""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
PEOPLE = {p["id"]: p for p in json.loads((ROOT / "data" / "people.json").read_text("utf-8"))["people"]}
QUESTIONS = json.loads((ROOT / "eval" / "questions.json").read_text("utf-8"))


def excerpt(q):
    return PEOPLE[q["person_id"]]["sources"][0]["excerpt"].lower()


def test_ten_questions_mixed_types_unique_ids():
    assert len(QUESTIONS) == 10
    assert len({q["id"] for q in QUESTIONS}) == 10
    assert {q["type"] for q in QUESTIONS} == {"answerable", "not_in_excerpt", "trap"}


def test_every_question_points_to_a_real_person():
    assert all(q["person_id"] in PEOPLE for q in QUESTIONS)


def test_answerable_keywords_really_appear_in_excerpt():
    for q in QUESTIONS:
        if q["type"] == "answerable":
            assert q["expect_keywords"], q["id"]
            assert all(k.lower() in excerpt(q) for k in q["expect_keywords"]), q["id"]


def test_not_in_excerpt_terms_really_absent_from_excerpt():
    for q in QUESTIONS:
        if q["type"] == "not_in_excerpt":
            assert q["absent_terms"], q["id"]
            assert not any(t.lower() in excerpt(q) for t in q["absent_terms"]), q["id"]
