from pathlib import Path

README = (Path(__file__).parent.parent / "README.md").read_text("utf-8")


def test_readme_states_the_default_context_and_reply_cap():
    assert "| `OLLAMA_NUM_CTX` | Context window sent to Ollama | `4096` |" in README
    assert "Longest reply the model may write | `150` tokens" in README


def test_readme_licence_and_credit_statements():
    assert "stay under **CC BY-SA 4.0**" in README and "**MIT**" in README
    assert "Wikipedia contributors, CC BY-SA 4.0" in README


def test_readme_has_no_stale_known_differences_line():
    assert "Known differences" not in README


RESULTS = (Path(__file__).parent.parent / "eval" / "results.md").read_text("utf-8")


def test_readme_results_table_matches_the_real_results_file():
    # Every totals row in the README must be copied from eval/results.md (no hand-typed numbers).
    rows = [l for l in RESULTS.splitlines() if l.startswith("| `") and (" | ON | " in l or " | OFF | " in l)]
    assert len(rows) == 2
    for row in rows:
        assert row in README


def test_readme_keeps_q07_separate_and_lists_known_limits():
    assert "## Known limits" in README and "**q07 is not fixed.**" in README
    assert "reported separately, not in the totals" in README


def test_readme_gemma_licence_is_link_only():
    assert "Licence: see the model page." in README
    assert "https://ollama.com/library/gemma4:e2b-it-qat" in README
    assert "Apache" not in README


def test_readme_never_claims_fine_tuning():
    for i in [m.start() for m in __import__("re").finditer("fine-tuned", README)]:
        assert README[max(0, i - 8):i] == "**not** ", README[max(0, i - 20):i + 12]


def test_readme_states_both_speed_figures_as_measured():
    assert "32.8 s per question" in README and "about 2 min 20 s" in README
    assert "not recorded by the app or the eval script" in README


def test_readme_keeps_required_submission_sections():
    for h in ("## AI disclosure", "## Team", "## Late commits"):
        assert h in README
