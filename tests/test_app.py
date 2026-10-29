"""Screen checks with a fake model (no Ollama). Uses the real data file."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

import narrator

APP = str(Path(__file__).parent.parent / "app.py")


def run(monkeypatch, person_index, reply):
    monkeypatch.setattr(narrator.OllamaClient, "generate", lambda self, s, u: reply)
    at = AppTest.from_file(APP).run()
    at.selectbox[0].select("Tech").run()
    at.selectbox[1].select_index(person_index).run()
    return at


def texts(at):
    return "\n".join(m.value for m in at.markdown) + "\n" + "\n".join(c.value for c in at.caption)


def test_team_note_is_labelled_and_prefix_not_doubled(monkeypatch):
    at = run(monkeypatch, 0, "{}")
    t = texts(at)
    assert "**Team note:** her protocols run quietly" in t
    assert "Team note: Team note" not in t and "Team note:** Team note" not in t


def test_answer_shows_ai_label_and_wikipedia_credit(monkeypatch):
    reply = '{"answer": "She invented the Spanning Tree Protocol.", "supporting_quote": "most famous for her invention of the Spanning Tree Protocol (STP)"}'
    at = run(monkeypatch, 0, reply)
    at.text_input[0].set_value("What is she famous for?").run()
    at.button[0].click().run()
    assert not at.exception
    t = texts(at)
    assert "AI-generated narration" in t
    assert "Wikipedia contributors, CC BY-SA 4.0" in t
    assert "https://en.wikipedia.org/wiki/Radia_Perlman" in t


def test_refusal_still_shows_credit(monkeypatch):
    at = run(monkeypatch, 1, '{"answer": "x", "supporting_quote": "made up words here"}')
    at.text_input[0].set_value("Anything?").run()
    at.button[0].click().run()
    t = texts(at)
    assert "That is not in my sources." in t and "Wikipedia contributors, CC BY-SA 4.0" in t
