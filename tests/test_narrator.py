import copy
import json
from pathlib import Path

import pytest
import requests

import narrator
from grounding import NOT_IN_SOURCES
from narrator import (ModelNotFound, NarratorError, OllamaClient, OllamaUnavailable,
                      answer_question, estimate_tokens, build_user_prompt, SYSTEM_PROMPT,
                      narration_from_raw)

PERSON = {
    "name": "Test Person",
    "sources": [{
        "title": "Test page", "url": "https://example.org/test", "licence": "CC BY-SA 4.0",
        "excerpt": "Test Person built the first widget in 1970. She worked at a small lab.",
    }],
}


class FakeModel:
    """Stands in for Ollama. Returns a fixed reply, or raises."""
    def __init__(self, reply="", error=None):
        self.reply, self.error, self.calls = reply, error, []

    def generate(self, system, user):
        self.calls.append((system, user))
        if self.error:
            raise self.error
        return self.reply


def reply(answer, quote):
    return json.dumps({"answer": answer, "supporting_quote": quote})


# ---- answer_question with a fake model -------------------------------------
def test_grounded_answer_is_shown_with_citation():
    m = FakeModel(reply("She built the first widget.", "built the first widget in 1970"))
    r = answer_question(m, PERSON, "What did she build?")
    assert r.status == "ok" and r.quote == "built the first widget in 1970"
    assert {k: r.citation[k] for k in ("title", "url", "licence")} == {
        "title": "Test page", "url": "https://example.org/test", "licence": "CC BY-SA 4.0"}
    assert set(r.citation) >= {"licence_url", "author"}


def test_made_up_quote_shows_not_in_sources():
    m = FakeModel(reply("She loved coffee.", "she loved coffee every morning"))
    r = answer_question(m, PERSON, "Did she like coffee?")
    assert r.status == "not_in_sources" and r.text == NOT_IN_SOURCES
    assert r.citation["url"] == "https://example.org/test"  # citation still shown


def test_model_says_cannot_answer():
    r = answer_question(FakeModel(reply("", "")), PERSON, "Where was she born?")
    assert r.status == "not_in_sources" and r.text == NOT_IN_SOURCES


@pytest.mark.parametrize("bad", ["", "I think so!", "{oops", "[1,2]"])
def test_bad_json_does_not_crash(bad):
    r = answer_question(FakeModel(bad), PERSON, "Anything?")
    assert r.status == "not_in_sources" and r.text == NOT_IN_SOURCES


def test_empty_question_never_calls_model():
    m = FakeModel(reply("x", "y"))
    assert answer_question(m, PERSON, "   ").status == "empty"
    assert m.calls == []


def test_client_error_becomes_friendly_message():
    m = FakeModel(error=OllamaUnavailable("Cannot reach Ollama"))
    r = answer_question(m, PERSON, "Hi?")
    assert r.status == "error" and "Cannot reach Ollama" in r.text


def test_person_without_source():
    assert answer_question(FakeModel(), {"name": "X", "sources": []}, "Hi?").status == "error"


def test_prompt_contains_the_rules_and_only_the_one_excerpt():
    m = FakeModel(reply("", ""))
    answer_question(m, PERSON, "Tell me more")
    system, user = m.calls[0]
    assert "ABOUT the person" in system and "Never invent a quote" in system
    assert "ONLY the EXCERPT" in system
    assert PERSON["sources"][0]["excerpt"] in user


# ---- context window ---------------------------------------------------------
def test_very_long_excerpt_is_refused_not_cut_off():
    long_person = {"name": "L", "sources": [dict(PERSON["sources"][0], excerpt="word " * 20000)]}
    m = FakeModel(reply("a", "b"))
    r = answer_question(m, long_person, "Q?")
    assert r.status == "too_long" and m.calls == []


def test_longest_real_excerpt_fits_in_context():
    data = json.loads((Path(__file__).parent.parent / "data" / "people.json").read_text("utf-8"))
    excerpts = [s["excerpt"] for p in data["people"] for s in p["sources"]]
    if not excerpts:
        pytest.skip("no people in data/people.json yet")
    longest = max(excerpts, key=len)
    person = {"name": "Longest", "sources": [dict(PERSON["sources"][0], excerpt=longest)]}
    total = estimate_tokens(SYSTEM_PROMPT) + estimate_tokens(build_user_prompt(person, longest, "Q?"))
    assert total <= narrator.DEFAULT_NUM_CTX - narrator.OUTPUT_TOKEN_RESERVE


# ---- OllamaClient with a mocked HTTP layer ---------------------------------
class FakeResponse:
    def __init__(self, status=200, body=None, text=""):
        self.status_code, self._body = status, body
        self.text = text or json.dumps(body or {})

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


def patch_post(monkeypatch, responses):
    sent = []
    it = iter(responses)

    def fake_post(url, json=None, timeout=None):
        sent.append((url, copy.deepcopy(json)))
        r = next(it)
        if isinstance(r, Exception):
            raise r
        return r
    monkeypatch.setattr(narrator.requests, "post", fake_post)
    return sent


def test_request_sets_model_num_ctx_json_format(monkeypatch):
    sent = patch_post(monkeypatch, [FakeResponse(body={"message": {"content": "{}"}})])
    OllamaClient(model="gemma4:e2b", num_ctx=8192).generate("s", "u")
    url, payload = sent[0]
    assert url.endswith("/api/chat")
    assert payload["model"] == "gemma4:e2b"
    assert payload["options"]["num_ctx"] == 8192
    assert payload["format"] == "json" and payload["stream"] is False


def test_thinking_text_is_ignored(monkeypatch):
    body = {"message": {"content": '{"answer":"a","supporting_quote":"b c d"}',
                        "thinking": "let me think {\"answer\": \"WRONG\"}"}}
    patch_post(monkeypatch, [FakeResponse(body=body)])
    out = OllamaClient(model="m").generate("s", "u")
    assert "WRONG" not in out


def test_model_not_found_message(monkeypatch):
    patch_post(monkeypatch, [FakeResponse(404, text='{"error":"model not found"}')])
    with pytest.raises(ModelNotFound) as e:
        OllamaClient(model="gemma4:nope").generate("s", "u")
    assert "ollama pull gemma4:nope" in str(e.value) and "ollama list" in str(e.value)


def test_ollama_not_running_message(monkeypatch):
    patch_post(monkeypatch, [requests.ConnectionError("refused")])
    with pytest.raises(OllamaUnavailable) as e:
        OllamaClient(model="m").generate("s", "u")
    assert "Start the Ollama app" in str(e.value)


def test_timeout_message(monkeypatch):
    patch_post(monkeypatch, [requests.Timeout("slow")])
    with pytest.raises(NarratorError):
        OllamaClient(model="m", timeout=5).generate("s", "u")


def test_retry_without_think_when_model_rejects_it(monkeypatch):
    sent = patch_post(monkeypatch, [
        FakeResponse(400, text='{"error":"model does not support think"}'),
        FakeResponse(body={"message": {"content": "{}"}}),
    ])
    OllamaClient(model="m").generate("s", "u")
    assert "think" in sent[0][1] and "think" not in sent[1][1]


def test_other_http_error(monkeypatch):
    patch_post(monkeypatch, [FakeResponse(500, text="boom")])
    with pytest.raises(NarratorError):
        OllamaClient(model="m").generate("s", "u")


def test_model_name_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "gemma4:e2b-it-qat")
    assert narrator.get_model_name() == "gemma4:e2b-it-qat"
    monkeypatch.delenv("OLLAMA_MODEL")
    assert narrator.get_model_name() == narrator.DEFAULT_MODEL


def test_timeout_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_TIMEOUT", "42")
    assert OllamaClient(model="m").timeout == 42.0
    monkeypatch.delenv("OLLAMA_TIMEOUT")
    assert OllamaClient(model="m").timeout == narrator.DEFAULT_TIMEOUT


# ---- grounding ON vs OFF (used by the eval) --------------------------------------
def test_grounding_off_accepts_an_invented_quote_that_grounding_on_refuses():
    raw = reply("She loved tea.", "she loved tea a lot")
    assert narration_from_raw(raw, PERSON, grounded=True).status == "not_in_sources"
    off = narration_from_raw(raw, PERSON, grounded=False)
    assert off.status == "ok" and off.text == "She loved tea."


def test_grounding_off_still_reports_bad_json_and_empty_answers():
    assert narration_from_raw("not json", PERSON, grounded=False).status == "bad_json"
    assert narration_from_raw(reply("", ""), PERSON, grounded=False).status == "not_in_sources"


def test_grounding_on_via_narration_from_raw_matches_answer_question():
    raw = reply("She built the first widget.", "built the first widget in 1970")
    assert narration_from_raw(raw, PERSON).status == "ok"


# ---- default context and output limits (decision of Fri Oct 30, 2026) ---------------
def test_default_context_is_4096_and_output_is_capped_at_150(monkeypatch):
    monkeypatch.delenv("OLLAMA_NUM_CTX", raising=False)
    assert narrator.DEFAULT_NUM_CTX == 4096
    assert narrator.MAX_OUTPUT_TOKENS == 150
    assert narrator.OUTPUT_TOKEN_RESERVE >= narrator.MAX_OUTPUT_TOKENS
    client = OllamaClient(model="m")
    assert client.num_ctx == 4096 and client.max_output_tokens == 150


def test_request_to_ollama_uses_4096_and_150_by_default(monkeypatch):
    monkeypatch.delenv("OLLAMA_NUM_CTX", raising=False)
    sent = patch_post(monkeypatch, [FakeResponse(body={"message": {"content": "{}"}})])
    OllamaClient(model="m").generate("s", "u")
    options = sent[0][1]["options"]
    assert options["num_ctx"] == 4096
    assert options["num_predict"] == 150
    assert options["temperature"] == 0


def test_num_ctx_can_still_be_raised_with_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_NUM_CTX", "8192")
    assert OllamaClient(model="m").num_ctx == 8192


def test_answer_question_default_budget_matches_4096():
    import inspect
    assert inspect.signature(answer_question).parameters["num_ctx"].default == 4096


def test_prompt_asks_for_short_answers_to_fit_the_output_cap():
    assert "one or two short" in SYSTEM_PROMPT and "3 to 25 words" in SYSTEM_PROMPT


def test_on_and_off_reasons_for_empty_answer_and_empty_quote():
    empty_answer = reply("", "")
    on, off = narration_from_raw(empty_answer, PERSON, True), narration_from_raw(empty_answer, PERSON, False)
    assert (on.status, on.reason) == ("not_in_sources", "empty_answer")
    assert (off.status, off.reason) == ("not_in_sources", "empty_answer")
    no_quote = reply("She did something.", "")
    on, off = narration_from_raw(no_quote, PERSON, True), narration_from_raw(no_quote, PERSON, False)
    assert (on.status, on.reason) == ("not_in_sources", "empty_quote")
    assert off.status == "ok"
