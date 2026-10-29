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
| Eval (`eval/run_eval.py`) | Script written. No real results yet, so there is no `eval/results.md`. |
| People and source texts | None added yet (`data/people.json` is an empty schema) |

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
| Labelled | The screen says "AI-generated narration" |

The check proves the quote is in the excerpt. It does not prove the answer is a good summary of that quote.

## How to run
1. Install [Ollama](https://ollama.com/download) and check it works: `ollama --version`
2. Download a model: `ollama pull gemma4:e4b` (or `ollama pull gemma4:e2b` for a smaller laptop). Check with `ollama list`.
3. Install the Python packages: `pip install -r requirements.txt`
4. Choose the model (skip this if you pulled `gemma4:e4b`):
   - Windows PowerShell: `$env:OLLAMA_MODEL="gemma4:e2b"`
   - Mac or Linux: `export OLLAMA_MODEL=gemma4:e2b`
5. Start the app: `streamlit run app.py`

Run the tests (no Ollama needed): `python -m pytest`

Run the eval (needs Ollama and the models installed; writes `eval/results.md` only after a real run):
`python eval/run_eval.py`. Choose models with `EVAL_MODELS=gemma4:e4b,gemma4:e2b`.

Settings:

| Variable | Meaning | Default |
|---|---|---|
| `OLLAMA_MODEL` | Model tag | `gemma4:e4b` |
| `OLLAMA_NUM_CTX` | Context window sent to Ollama | `8192` |
| `OLLAMA_HOST_URL` | Where Ollama runs | `http://localhost:11434` |

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
- Source excerpts will be copied word for word from Wikipedia pages and stay under **CC BY-SA 4.0**. Each entry in `data/people.json` records the page title, URL, licence and the date copied.
- The code in this repo is **MIT** licensed. The excerpts keep their own CC BY-SA 4.0 licence.
- Gemma 4: see the model page links above.

| Person | Genre | Source | State |
|---|---|---|---|
| Radia Perlman | Tech | Wikipedia | Not added yet |
| Gladys West | Tech | Wikipedia | Not added yet |

## AI disclosure
Narration is AI-generated. People and sources were chosen by humans.

## Team
DEV: @chebitoch007, @faith_mugi_

## Late commits
Any commit made after Sun Nov 1, 2026, 09:59 EAT is listed here.
