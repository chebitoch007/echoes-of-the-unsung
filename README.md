# Echoes of the Unsung

A small tool for the Hacktoberfest Open-Source AI Challenge, Week 4: Ghost in the Machine.

Pick a genre (Tech, Agri, Education), pick a person who shaped society but got little credit, and ask a ghost narrator about them. Answers come only from a fixed source text and always show the citation.

## Status
Work in progress. Started Wed Oct 28, 2026, inside the challenge window.
Submission deadline: Sun Nov 1, 2026, 09:59 EAT.

| Part | State |
|---|---|
| Data file (`data/people.json`) | Empty schema, no people yet |
| App (`app.py`) | Streamlit skeleton, genre and person pickers work |
| Open-source model | Not connected yet |
| Source texts and citations | Not added yet |

## Open-source AI used
(To fill in: model name, how it runs locally.)

## How to run
```
pip install streamlit
streamlit run app.py
```
Until people are added to the data file, the app shows "No people added yet."

## Project layout
| Path | What it is |
|---|---|
| `app.py` | Streamlit app: pick a genre, pick a person, ask the ghost |
| `data/people.json` | People and their source texts (schema is documented inside the file) |

## Sources and credits
(Every source text, its licence, and a link.)

## AI disclosure
Narration is AI-generated. People and sources were chosen by humans.

## Team
DEV: @chebitoch007, @faith_mugi_

## Late commits
Any commit made after Sun Nov 1, 2026, 09:59 EAT is listed here.
