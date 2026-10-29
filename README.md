# Echoes of the Unsung

A small tool for the Hacktoberfest Open-Source AI Challenge, Week 4: Ghost in the Machine.

Pick a genre (Tech, Agri, Education), pick a person who shaped society but got little credit, and ask a ghost narrator about them. Answers come only from a fixed source text and always show the citation.

## Status
Work in progress. Started Wed Oct 28, 2026, inside the challenge window.
Submission deadline: Sun Nov 1, 2026, 09:59 EAT.

| Part | State |
|---|---|
| Screen (`app.py`) | Written. Checked with a fake model in a test run. |
| Model call (`narrator.py`) | Written. Unit-tested with a fake model. Not yet run against a real Gemma 4 model. |
| Safety check (`grounding.py`) | Written and unit-tested. |
| People and source texts | 6 people added (2 Tech, 2 Agri, 2 Education). Excerpts copied from Wikipedia on 2026-10-29. |
| Screen details | Shows the "Team note" for each person (labelled, not part of the source) and "Wikipedia contributors, CC BY-SA 4.0" with every citation |
| Tests | 83 pass with a fake model, including a grounding test for each of the 6 people |
| Eval | 10 questions and a runner are written. No real run yet, so there is no `eval/results.md`. |

## Open-source AI used
**Gemma 4** (Google, open-weight), run locally through [Ollama](https://ollama.com). The app talks only to Ollama on your own computer (`localhost:11434`).

- Default model tag: `gemma4:e4b`. On a smaller laptop use `gemma4:e2b` (or any tag shown by `ollama list`).
- The model is used as it comes. It is **not** fine-tuned.
- Why open weights matter here: the model runs on the person's own machine, needs no API key, and sends no questions to an outside service. Anyone can run the same model and check the results.
- Licence: see the model page. [Gemma with Ollama (Google)](https://ai.google.dev/gemma/docs/integrations/ollama), [Gemma 4 in the Ollama library](https://ollama.com/library/gemma4).

How the ghost stays honest:

| Rule | How it is done |
|---|---|
| Speaks about the person, never as the person | Instruction in the prompt (`narrator.py`) |
| No invented quotes | Instruction in the prompt, plus a code check that rejects quoted words that are not in the excerpt |
| Answers only from one excerpt | The prompt contains only that excerpt |
| Every answer is backed by the source | The model must return a `supporting_quote`. Code checks it appears word for word in the excerpt (spaces and case ignored). If not: "That is not in my sources." |
| Living people (Perlman, Wambugu) | The prompt tells the model the person is living and to state only what the excerpt says. The narrator speaks about them, never as them. |
| Vague wording in the source | The prompt says not to guess what a vague reference means. For Wambugu's 2004 line ("the project had failed"), a code guard also refuses any answer that says "fail" and names a project the excerpt does not name. |
| Labelled | The screen says "AI-generated narration" |

The check proves the quote is in the excerpt. It does not prove the answer is a good summary of that quote.

## How to run
1. Install [Ollama](https://ollama.com/download) and check it works: `ollama --version`
2. Download a model and check it with `ollama list`:
   - 16 GB RAM or more: `ollama pull gemma4:e4b`
   - Smaller laptop: a smaller Gemma 4 tag. The team's 8 GB laptop uses `gemma4:e2b-it-qat` (4.3 GB).
3. Install the Python packages: `pip install -r requirements.txt`
4. Tell the app which model you pulled (skip this if you pulled `gemma4:e4b`):
   - Windows PowerShell: `$env:OLLAMA_MODEL="gemma4:e2b-it-qat"`
   - Mac or Linux: `export OLLAMA_MODEL=gemma4:e2b-it-qat`
5. Start the app: `streamlit run app.py`

Run the tests (no Ollama needed): `python -m pytest`

Run the eval (needs Ollama and the models installed; writes `eval/results.md` only after a real run):
`python eval/run_eval.py`. Choose models with `EVAL_MODELS`, for example `$env:EVAL_MODELS="gemma4:e2b-it-qat"`.

Settings:

| Variable | Meaning | Default |
|---|---|---|
| `OLLAMA_MODEL` | Model tag | `gemma4:e4b` |
| `OLLAMA_NUM_CTX` | Context window sent to Ollama | `8192` |
| `OLLAMA_TIMEOUT` | Seconds to wait for a reply (first reply is slower while the model loads) | `300` |
| `OLLAMA_HOST_URL` | Where Ollama runs | `http://localhost:11434` |
| `EVAL_MODELS` | Models the eval compares | `gemma4:e4b,gemma4:e2b` |

Tested so far: Python 3.12 and Streamlit 1.66 in a test environment, with a fake model. Not yet tested with a real model.

## Project layout
| Path | What it is |
|---|---|
| `app.py` | Streamlit screen only: pick a genre, pick a person, ask, see the answer and citation |
| `narrator.py` | Calls the local model through Ollama; builds the prompt |
| `grounding.py` | Checks the model's quote against the excerpt |
| `data/people.json` | People and their source texts (schema is documented inside the file) |
| `tests/` | pytest tests using a fake model |
| `eval/` | Eval questions and runner |

## Sources and credits
- Source excerpts are copied from Wikipedia pages and stay under **CC BY-SA 4.0** ([licence text](https://creativecommons.org/licenses/by-sa/4.0/)). The code in this repo is **MIT** licensed. The excerpts keep their own CC BY-SA 4.0 licence.
- Every citation in the app shows "Wikipedia contributors, CC BY-SA 4.0", the page title, the URL and the supporting quote. The authors of each page are listed in its Wikipedia page history.
- Each entry in `data/people.json` records the page title, URL, licence, the date copied and the page's last-edited time.
- Excerpts were copied from page text pasted by a team member on 2026-10-29. Citation markers like [1] were removed. Passages from different parts of a page are separated by a blank line.
- The "Team note" lines (`why_unsung`) and the `years` field are written by the team. They are not Wikipedia text, and the app labels them.
- Gemma 4: see the model page links above.

| Person | Genre | Living | Source page | Page last edited (UTC) |
|---|---|---|---|---|
| Radia Perlman | Tech | Yes | [Wikipedia](https://en.wikipedia.org/wiki/Radia_Perlman) | 2026-09-18 13:52 |
| Gladys West | Tech | No | [Wikipedia](https://en.wikipedia.org/wiki/Gladys_West) | 2026-10-10 18:57 |
| E. K. Janaki Ammal | Agri | No | [Wikipedia](https://en.wikipedia.org/wiki/Janaki_Ammal) | 2026-10-06 13:47 |
| Florence Wambugu | Agri | Yes | [Wikipedia](https://en.wikipedia.org/wiki/Florence_Wambugu) | 2026-09-14 08:41 |
| Savitribai Phule | Education | No | [Wikipedia](https://en.wikipedia.org/wiki/Savitribai_Phule) | 2026-10-15 17:23 |
| James Emman Kwegyir Aggrey | Education | No | [Wikipedia](https://en.wikipedia.org/wiki/James_Emman_Kwegyir_Aggrey) | 2026-10-23 22:37 |

Known differences from the live pages (checked Thu Oct 29, 2026): the Perlman and Phule excerpts do not match the live Wikipedia text word for word in 4 places. The other four match. These differences are not fixed yet.

## AI disclosure
Narration is AI-generated. People and sources were chosen by humans.

## Team
DEV: @chebitoch007, @faith_mugi_

## Late commits
Any commit made after Sun Nov 1, 2026, 09:59 EAT is listed here.
