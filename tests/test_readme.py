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
