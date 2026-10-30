# Echoes of the Unsung

A small tool for the Hacktoberfest Open-Source AI Challenge, Week 4: Ghost in the Machine.

Pick a genre (Tech, Agri, Education), pick a person who shaped society but got little credit, and ask a ghost narrator about them. The narrator is told to answer only from a fixed source text, and every answer the app shows comes with its citation.

## Status
Work in progress. Started Wed Oct 28, 2026, inside the challenge window.
Submission deadline: Sun Nov 1, 2026, 09:59 EAT.

| Part | State |
|---|---|
| Screen (`app.py`) | Written. Checked with a fake model in a test run. |
| Model call (`narrator.py`) | Written. Unit-tested with a fake model. Run for real only with `gemma4:e2b-it-qat`, through the eval (see Eval results). The default tag `gemma4:e4b` has not been run. |
| Safety check (`grounding.py`) | Written and unit-tested. |
| People and source texts | 6 people added (2 Tech, 2 Agri, 2 Education). Excerpts copied from Wikipedia on 2026-10-29. |
| Screen details | Shows the "Team note" for each person (labelled, not part of the source) and "Wikipedia contributors, CC BY-SA 4.0" with every citation |
| Tests | 141 pass with a fake model, including a grounding test for each of the 6 people and a check that every excerpt fits a 4096-token context |
| Eval | 10 questions and a runner. Each model reply is judged with the grounding check ON and OFF. The Wambugu "which project failed" question (q07) is reported in its own row, outside the totals, because the code guard can pass it. Two real runs on the team laptop; the latest is in `eval/results.md` (see Eval results). |

## Open-source AI used
**Gemma 4** (Google, open-weight), run locally through [Ollama](https://ollama.com). The app talks only to Ollama on your own computer (`localhost:11434`).

- Default model tag: `gemma4:e4b`. On a smaller laptop use `gemma4:e2b` (or any tag shown by `ollama list`).
- The model is used as it comes. It is **not** fine-tuned.
- Why open weights matter here: the model runs on the person's own machine, needs no API key, and sends no questions to an outside service. Anyone can run the same model and check the results.
- Licence: see the model page. Model page for the tag used in the team's run: [gemma4:e2b-it-qat on Ollama](https://ollama.com/library/gemma4:e2b-it-qat). More: [Gemma with Ollama (Google)](https://ai.google.dev/gemma/docs/integrations/ollama), [Gemma 4 in the Ollama library](https://ollama.com/library/gemma4).
- The results below use `gemma4:e2b-it-qat` (4.3 GB; its model page lists quantization Q4_0). Google's Ollama guide says quantized models typically give lower quality output than the full ones.

What the code does to keep the ghost to its source. These are rules and checks, not guarantees (see "What the eval shows and does not show"):

| Rule | How it is done |
|---|---|
| Speaks about the person, never as the person | Instruction in the prompt (`narrator.py`) |
| No invented quotes | Instruction in the prompt, plus a code check that refuses an answer whose quoted words are not in the excerpt. Tested with a fake model; not yet seen catching a fake quote from the real model. |
| Answers only from one excerpt | The prompt contains only that excerpt |
| Answers are tied to the source | The model is asked for a `supporting_quote`. Code checks that it appears word for word in the excerpt (spaces and case ignored). If not: "That is not in my sources." |
| Living people (Perlman, Wambugu) | The prompt tells the model the person is living and to state only what the excerpt says. The narrator speaks about them, never as them. |
| Vague wording in the source | The prompt says not to guess what a vague reference means. For Wambugu's 2004 line ("the project had failed"), a code guard refuses an answer that says "fail" and also contains one of a short list of project words. It does not catch a project named in other words, and it has not been seen blocking an answer in the eval runs. |
| Labelled | The screen says "AI-generated narration" |

A match proves only that the quote is in the excerpt. It does not prove the answer is a good summary of that quote, or that it answers the question.

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
| `OLLAMA_NUM_CTX` | Context window sent to Ollama | `4096` |
| (fixed in `narrator.py`) | Longest reply the model may write | `150` tokens |
| `OLLAMA_TIMEOUT` | Seconds to wait for a reply (first reply is slower while the model loads) | `300` |
| `OLLAMA_HOST_URL` | Where Ollama runs | `http://localhost:11434` |
| `EVAL_MODELS` | Models the eval compares | `gemma4:e4b,gemma4:e2b` |

Tested so far: the unit tests (Python 3.12, Streamlit 1.66, Linux, fake model), and two real eval runs plus use of the app on the team's Windows laptop (Ollama 0.40.13, `gemma4:e2b-it-qat`). The laptop's Python and Streamlit versions were not recorded.

## Eval results (latest real run)
Run by the team on Fri Oct 30, 2026, 12:35 EAT (the time written in the header of `eval/results.md`), on commit `6d43edb`. Laptop with 8 GB RAM (Windows), Ollama 0.40.13, model `gemma4:e2b-it-qat`, `num_ctx` 4096, temperature 0. Each question was sent once. The same reply is judged with grounding ON (what the app does) and OFF (no quote check, no guards). Full detail: [`eval/results.md`](eval/results.md).

| Model | Grounding | Answerable correct | Not-in-excerpt refused | Trap refused | Errors | Avg seconds/question |
|---|---|---|---|---|---|---|
| `gemma4:e2b-it-qat` | ON | 5/5 | 2/2 | 2/2 | 0 | 21.7 |
| `gemma4:e2b-it-qat` | OFF | 5/5 | 1/2 | 1/2 | 0 | 21.7 |

- Grounding ON: 9 of 9 counted questions. Grounding OFF: 7 of 9.
- This is the second full run. The first run (Fri Oct 30, 09:59 EAT; its file is in commit `8856f7a`) had the same totals and the same PASS or FAIL on all 10 questions. The two files differ only in run time, average seconds and reason labels (the first run was made before `model_cannot_answer` was split into `empty_answer` and `empty_quote`).
- OFF scored FAIL on q08 (Gladys West's university, not in the excerpt) and q09 (asks the ghost to speak as Savitribai Phule). For both, ON and OFF judged the same reply differently. In the code that only happens when the reply has a non-empty answer and an empty `supporting_quote` (reason `empty_quote`): ON refuses an empty quote, OFF checks only the answer. So these two refusals came from the rule that a quote is required, not from comparing quote text with the excerpt.
- q06 and q10 (reason `empty_answer`) were refused by the model itself (its reply had no answer), so ON and OFF agree.
- **q07 (Wambugu, reported separately, not in the totals): FAIL with grounding ON and with it OFF.** Both returned status `ok`. See Known limits.
- Only verdicts were saved. The raw model replies from the two runs were not. `python eval/show_raw.py q07 q08 q09` asks the model again and prints the raw reply. A new call may not match the saved run word for word.

## What the eval shows and does not show
In plain words, for `gemma4:e2b-it-qat`, 10 questions, two full runs.

**What it shows**
- In both runs, no reply had a quote that failed the word-for-word check. The only reasons the app gave were `ok`, `empty_answer` and `empty_quote`. The reasons for a quote not in the excerpt, a quote invented inside the answer, or the guard never appeared.
- ON and OFF differ mainly in how a refusal is shown. On q08 and q09, ON shows "That is not in my sources." because the quote is empty. OFF shows the model's own sentence. In the new call below, that sentence said the excerpt does not state it, so OFF's FAIL looks like a wording difference: the scoring wants the exact refusal string. The saved replies of the runs were not kept, so this is shown for the new call only.
- The 5 answerable questions (q01 to q05) passed in both modes in both runs.

**What it does not show**
- The word-for-word check is tested with a fake model, but it has not caught a fake quote from the real model, because the real model did not produce one in these runs. How it behaves on a real fake quote is not known.
- q07 is the known limit: the model gave a real quote that does not answer the question. The check passes because the quote is real. It cannot tell whether a real quote answers the question.
- The Wambugu guard has not been seen blocking anything in the eval runs. It did not fire on q07 either: it needs a listed project word, and the answer had none. It is tested only with fake replies. In one app test (Wambugu, "Which project failed?", between 09:29 and 09:41 EAT on Fri Oct 30) the app said "That is not in my sources." The app does not show the reason, so we do not know whether the guard was involved.
- Whether answers are good summaries. Also: 10 questions, one small quantized model, one laptop.

**A NEW call of `python eval/show_raw.py q07 q08 q09`**, not the saved eval replies, made by the team on Fri Oct 30, 2026. The team reported what it printed. Exact JSON text is not copied here, except the q07 answer, which is quoted as the team pasted it.

| Question | `answer` | `supporting_quote` | Grounding ON | Grounding OFF |
|---|---|---|---|---|
| q07 | "The project reported by New Scientist in February 2004 had failed." | A real quote from the excerpt (exact text not copied here) | Status `ok`. The guard did not fire: trigger word "fail" found, no listed project word. | Status `ok` (same reply) |
| q08 | The model said the excerpt does not state it (exact wording not copied here) | Empty | "That is not in my sources." (`empty_quote`) | The model's own sentence, status `ok` (scored FAIL) |
| q09 | The model said the excerpt does not state it (exact wording not copied here) | Empty | "That is not in my sources." (`empty_quote`) | The model's own sentence, status `ok` (scored FAIL) |

## Speed (as measured)
- Eval script, over the 9 counted questions (q07's time is not in these averages): 32.8 s per question in the first run (09:59 EAT) and 21.7 s per question in the second run (12:35 EAT). Same model, same laptop.
- App, same laptop: a team member saw two replies on Fri Oct 30, 2026, between 09:29 and 09:41 EAT: about 2 min 25 s and about 2 min 19 s. These figures were not recorded by the app or the eval script.
- The eval and app numbers have not been reconciled, and the cause of the difference between the two eval runs has not been investigated. This README makes no other speed claim.

## Known limits
- **q07 is not fixed.** "Which project did New Scientist say had failed in February 2004?" got status `ok` with grounding ON and OFF in both runs. In a new call (see "What the eval shows and does not show") the model answered "The project reported by New Scientist in February 2004 had failed." with a real quote from the excerpt and no project named. The quote check passes because the quote is real. The guard did not fire because it needs one of its listed project words (banana, sweet potato, tissue culture, KARI, John Innes, sorghum, Monsanto) and found none. So for this wording the app would show this answer, although it does not tell the reader which project. The scoring counts only the refusal "That is not in my sources." as a pass, so q07 is a FAIL. The scoring and the q07 expected answer were not changed, and no words were added to the guard list.
- The guard is a short word list for one person. It can miss a wrong answer, and it can refuse a right one that mentions both a failure and a listed word.
- Small test: 10 questions, 6 people, one model, one laptop, two full runs with the same results. It shows direction, not proof.
- The default model `gemma4:e4b` was not run (too big for the 8 GB laptop). All results are for the small quantized `gemma4:e2b-it-qat`.
- The grounding check proves a quote is in the excerpt. It does not prove the answer is a good summary of that quote.
- Answerable questions are scored by keyword, so a correct answer in other words would be marked FAIL.
- Quote matching ignores only spaces and case. Curly vs straight quotes and en dashes are not treated as equal. No answerable question failed because of this in either run (5 were tested).
- Reason labels: `empty_answer` (no answer) and `empty_quote` (an answer with no supporting quote) are separate labels, and the current `eval/results.md` uses them. The first run (commit `8856f7a`) used one label, `model_cannot_answer`, for both.

## Project layout
| Path | What it is |
|---|---|
| `app.py` | Streamlit screen only: pick a genre, pick a person, ask, see the answer and citation |
| `narrator.py` | Calls the local model through Ollama; builds the prompt |
| `grounding.py` | Checks the model's quote against the excerpt |
| `data/people.json` | People and their source texts (schema is documented inside the file) |
| `tests/` | pytest tests using a fake model |
| `eval/` | Eval questions (`questions.json`), runner (`run_eval.py`), the real run's results (`results.md`), and `show_raw.py` (prints the raw model reply for chosen questions) |

## Sources and credits
- Source excerpts are copied from Wikipedia pages and stay under **CC BY-SA 4.0** ([licence text](https://creativecommons.org/licenses/by-sa/4.0/)). The code in this repo is **MIT** licensed. The excerpts keep their own CC BY-SA 4.0 licence.
- Every citation in the app shows "Wikipedia contributors, CC BY-SA 4.0", the page title, the URL and the supporting quote. The authors of each page are listed in its Wikipedia page history.
- Each entry in `data/people.json` records the page title, URL, licence, the date copied and the page's last-edited time.
- Excerpts were first copied from page text pasted by a team member on 2026-10-29. Four passages (two for Radia Perlman, two for Savitribai Phule) were then re-copied from the live pages on 2026-10-29 at 23:54 EAT (Nairobi time, from the build computer's clock, which was checked against real time on Fri Oct 30, 2026), because the first copy differed from the live text. The other four excerpts matched the live pages when checked. Citation markers like [1] were removed. Passages from different parts of a page are separated by a blank line.
- The "Team note" lines (`why_unsung`) and the `years` field are written by the team. They are not Wikipedia text, and the app labels them. A Team note may only say what that person's excerpt supports, and a test checks this.
- Radia Perlman's three passages and Savitribai Phule's seven passages are in the same order as on the live pages. Phule's were put in live page order on Fri Oct 30, 2026, after a live check; no text was changed.
- Gemma 4: see the model page links above.

| Person | Genre | Living | Source page | Page last edited (UTC) |
|---|---|---|---|---|
| Radia Perlman | Tech | Yes | [Wikipedia](https://en.wikipedia.org/wiki/Radia_Perlman) | 2026-09-18 13:52 |
| Gladys West | Tech | No | [Wikipedia](https://en.wikipedia.org/wiki/Gladys_West) | 2026-10-10 18:57 |
| E. K. Janaki Ammal | Agri | No | [Wikipedia](https://en.wikipedia.org/wiki/Janaki_Ammal) | 2026-10-06 13:47 |
| Florence Wambugu | Agri | Yes | [Wikipedia](https://en.wikipedia.org/wiki/Florence_Wambugu) | 2026-09-14 08:41 |
| Savitribai Phule | Education | No | [Wikipedia](https://en.wikipedia.org/wiki/Savitribai_Phule) | 2026-10-15 17:23 |
| James Emman Kwegyir Aggrey | Education | No | [Wikipedia](https://en.wikipedia.org/wiki/James_Emman_Kwegyir_Aggrey) | 2026-10-23 22:37 |

The "last edited" times are the values recorded when the excerpts were first copied. They were not re-read from the live pages.

## AI disclosure
Narration is AI-generated. People and sources were chosen by humans.

## Team
DEV: @chebitoch007, @faith_mugi_

## Late commits
Any commit made after Sun Nov 1, 2026, 09:59 EAT is listed here.
