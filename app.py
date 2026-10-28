"""Echoes of the Unsung: minimal Streamlit skeleton.

Pick a genre, pick a person, ask the ghost narrator.
Answers must come only from the fixed source text in data/people.json,
and every answer must show its citation.
The narrator (open-source model) is not wired in yet.
"""
import json
from pathlib import Path

import streamlit as st

DATA_FILE = Path(__file__).parent / "data" / "people.json"


@st.cache_data
def load_data():
    with DATA_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def main():
    st.set_page_config(page_title="Echoes of the Unsung", page_icon="👻")
    st.title("Echoes of the Unsung")
    st.caption("Hacktoberfest Week 4: Ghost in the Machine")

    data = load_data()
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
    question = st.text_input("Ask the ghost")

    if question:
        # TODO: call the local open-source model, restricted to person["sources"].
        st.write("The ghost is not awake yet (model not connected).")
        for s in person["sources"]:
            st.caption(f"Source: {s['title']} ({s['licence']}) {s['url']}")


main()
