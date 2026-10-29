"""Runs the grounding check on the REAL people in data/people.json.

For each person there is one question where the fake model gives a real quote,
and one where it invents a quote. No Ollama needed.
"""
import json
import os
from pathlib import Path

import pytest

from grounding import NOT_IN_SOURCES, check_answer
from narrator import answer_question, build_user_prompt

ROOT = Path(__file__).parent.parent
DATA = json.loads((ROOT / "data" / "people.json").read_text("utf-8"))
PEOPLE = {p["id"]: p for p in DATA["people"]}


class FakeModel:
    def __init__(self, answer, quote):
        self.reply = json.dumps({"answer": answer, "supporting_quote": quote})
        self.last_user = ""

    def generate(self, system, user):
        self.last_user = user
        return self.reply


# (person id, question, answer the fake model gives, REAL quote copied from that person's excerpt)
REAL = [
    ("radia-perlman", "What is she most famous for?",
     "She is most famous for inventing the Spanning Tree Protocol.",
     "most famous for her invention of the Spanning Tree Protocol (STP)"),
    ("gladys-west", "Why did satellites need her work?",
     "The source says Earth is not a sphere, so satellites need very accurate models of its shape.",
     "Since Earth is not actually a sphere"),
    ("janaki-ammal", "What did she do for sugarcane?",
     "She created a high yielding sugarcane strain that suited Indian conditions.",
     "create a high yielding strain of the sugarcane"),
    ("florence-wambugu", "What crop did she modify?",
     "She developed a virus-resistant genetically modified sweet potato.",
     "She developed a genetically modified virus-resistant sweet potato."),
    ("savitribai-phule", "How many schools did the couple open?",
     "The couple opened 18 schools in total.",
     "In total, the couple opened 18 schools"),
    ("james-aggrey", "What was his job at Achimota College?",
     "He was the first Vice Principal of Achimota College.",
     "first Vice Principal of Achimota College"),
]


def test_every_person_is_covered_by_a_test():
    assert {r[0] for r in REAL} == set(PEOPLE)


@pytest.mark.parametrize("pid,question,answer,quote", REAL)
def test_real_quote_is_accepted_and_cited(pid, question, answer, quote):
    person = PEOPLE[pid]
    excerpt = person["sources"][0]["excerpt"]
    assert check_answer(json.dumps({"answer": answer, "supporting_quote": quote}), excerpt,
                        person.get("guards")).ok
    n = answer_question(FakeModel(answer, quote), person, question)
    assert n.status == "ok" and n.quote == quote
    assert n.citation["author"] == "Wikipedia contributors"
    assert n.citation["licence"] == "CC BY-SA 4.0"
    assert n.citation["url"].startswith("https://en.wikipedia.org/wiki/")


@pytest.mark.parametrize("pid,question,answer,quote", REAL)
def test_invented_quote_is_refused_for_every_person(pid, question, answer, quote):
    person = PEOPLE[pid]
    n = answer_question(FakeModel("Invented.", "I always knew this would change the world"), person, question)
    assert n.status == "not_in_sources" and n.text == NOT_IN_SOURCES
    assert n.citation["author"] == "Wikipedia contributors"  # citation still shown on refusal


@pytest.mark.parametrize("pid,question,answer,quote", REAL)
def test_made_up_words_in_quote_marks_are_refused(pid, question, answer, quote):
    person = PEOPLE[pid]
    fake = f'The source says "{quote}" and also "I never wanted any thanks for this".'
    n = answer_question(FakeModel(fake, quote), person, question)
    assert n.status == "not_in_sources"


def test_aggrey_real_quotation_is_allowed():
    person = PEOPLE["james-aggrey"]
    n = answer_question(
        FakeModel('The source quotes him: "if you educate a woman, you educate a whole nation".',
                  "if you educate a woman, you educate a whole nation"),
        person, "What did he say about educating women?")
    assert n.status == "ok"


# ---- living people and the vague "project" -------------------------------------
@pytest.mark.parametrize("pid,living", [("radia-perlman", True), ("florence-wambugu", True),
                                        ("gladys-west", False), ("janaki-ammal", False),
                                        ("savitribai-phule", False), ("james-aggrey", False)])
def test_living_flags_and_prompt_status(pid, living):
    person = PEOPLE[pid]
    assert person["living"] is living
    prompt = build_user_prompt(person, "x", "q")
    assert ("PERSON STATUS: living" in prompt) is living


WAMBUGU = PEOPLE["florence-wambugu"]
FAILED_QUOTE = "reported that the project had failed"


def test_wambugu_2004_report_without_naming_a_project_is_ok():
    n = answer_question(
        FakeModel("In February 2004 New Scientist reported that the project had failed.", FAILED_QUOTE),
        WAMBUGU, "What did New Scientist report?")
    assert n.status == "ok"


@pytest.mark.parametrize("named", ["banana", "sweet potato", "tissue culture", "sorghum", "Monsanto"])
def test_wambugu_naming_a_project_is_refused(named):
    n = answer_question(
        FakeModel(f"New Scientist reported that the {named} project had failed.", FAILED_QUOTE),
        WAMBUGU, "Which project failed?")
    assert n.status == "not_in_sources" and n.reason == "guard_unsupported_link"


def test_guard_only_applies_to_the_person_who_has_one():
    west = PEOPLE["gladys-west"]
    n = answer_question(FakeModel("The banana project failed in a sphere.", "Since Earth is not actually a sphere"),
                        west, "Q?")
    assert n.status == "ok"  # no guard on West


def test_prompt_tells_model_not_to_name_vague_references():
    from narrator import SYSTEM_PROMPT
    assert "vaguely" in SYSTEM_PROMPT and "the project" in SYSTEM_PROMPT
    assert "never as" in SYSTEM_PROMPT.lower() or "Never speak AS the person" in SYSTEM_PROMPT


# ---- schema doc -------------------------------------------------------------------
def test_schema_doc_lists_required_fields():
    top = set(DATA["fields"])
    src = set(DATA["fields"]["sources"][0])
    assert "living" in top
    assert {"licence_url", "retrieved", "page_last_edited_utc", "note"} <= src
    assert {"author", "guards"} <= (top | src)


def test_every_source_has_the_required_metadata():
    need = set(DATA["fields"]["sources"][0])
    for p in DATA["people"]:
        assert need <= set(p["sources"][0]), p["id"]
        assert p["sources"][0]["licence"] == "CC BY-SA 4.0"
        assert p["why_unsung"].startswith("Team note:")
