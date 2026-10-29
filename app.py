"""Echoes of the Unsung: the Streamlit screen only.

Pick a genre, pick a person, ask a question. The ghost narrator answers from
one source excerpt, and the answer is shown with its citation.
Logic lives in narrator.py (model call) and grounding.py (safety check).
"""
import json
import os
from pathlib import Path

import streamlit as st

from narrator import OllamaClient, answer_question, get_model_name

DATA_FILE = Path(os.environ.get("ECHOES_DATA", Path(__file__).parent / "data" / "people.json"))


@st.cache_data
def load_data(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_resource
def get_client(model: str):
    return OllamaClient(model=model)


def show_citation(n):
    c = n.citation
    if not c:
        return
    credit = f"{c.get('author') or 'Unknown author'}, {c['licence']}"
    st.markdown("**Citation**")
    st.markdown(
        f"- Credit: {credit}\n"
        f"- Source: {c['title']}\n"
        f"- URL: {c['url']}\n"
        f"- Licence: {c['licence']}" + (f" ({c['licence_url']})" if c.get("licence_url") else "") + "\n"
        f"- Supporting quote: {('\u201c' + n.quote + '\u201d') if n.quote else 'none (no supported answer)'}"
    )


def team_note(person):
    """The why_unsung line, without its 'Team note:' prefix (the screen adds a label)."""
    note = (person.get("why_unsung") or "").strip()
    return note[len("Team note:"):].strip() if note.lower().startswith("team note:") else note


def main():
    st.set_page_config(page_title="Echoes of the Unsung", page_icon="👻")
    st.title("Echoes of the Unsung")
    st.caption("Hacktoberfest Week 4: Ghost in the Machine")

    model = get_model_name()
    st.sidebar.markdown(f"**Model (runs locally):** `{model}`")

    data = load_data(str(DATA_FILE))
    people = data.get("people", [])
    if not people:
        st.info("No people added yet. Add entries to data/people.json.")
        return

    genre = st.selectbox("Genre", data["genres"])
    in_genre = [p for p in people if p["genre"] == genre]
    if not in_genre:
        st.warning(f"No one in {genre} yet.")
        return

    person = st.selectbox("Person", in_genre, format_func=lambda p: p["name"])
    if person.get("living"):
        st.caption("This person is living. The ghost only describes what the source says about them.")

    note = team_note(person)
    if note:
        st.markdown(f"**Team note:** {note}")
        st.caption("Written by the team. It is not part of the source text.")

    question = st.text_input("Ask the ghost")
    if st.button("Ask") and question.strip():
        with st.spinner("The ghost is thinking..."):
            n = answer_question(get_client(model), person, question)
        st.markdown("**👻 AI-generated narration**")
        if n.status == "ok":
            st.write(n.text)
        elif n.status == "error":
            st.error(n.text)
        else:
            st.write(n.text)
        if n.status in ("ok", "not_in_sources"):
            show_citation(n)


main()
