import json

from grounding import check_answer, normalise, parse_model_json, quote_in_excerpt

EXCERPT = "The  quick brown fox jumps over the lazy dog.\nIt was a sunny day."


def raw(answer, quote):
    return json.dumps({"answer": answer, "supporting_quote": quote})


def test_normalise_ignores_spaces_and_case():
    assert normalise("  A   b\nC ") == "a b c"


def test_quote_found_ignoring_case_and_spacing():
    assert quote_in_excerpt("QUICK   brown fox", EXCERPT)


def test_quote_across_single_line_break():
    assert quote_in_excerpt("lazy dog. it was", EXCERPT)


def test_quote_cannot_join_two_passages():
    two = "First passage ends here.\n\nSecond passage starts there."
    assert quote_in_excerpt("passage ends here.", two)
    assert not quote_in_excerpt("passage ends here. Second passage starts", two)


def test_quote_not_in_excerpt():
    assert not quote_in_excerpt("quick red fox", EXCERPT)


def test_too_short_quote_rejected():
    assert not quote_in_excerpt("the", EXCERPT)


def test_good_answer_accepted():
    r = check_answer(raw("A fox jumped.", "brown fox jumps over"), EXCERPT)
    assert r.ok and r.quote == "brown fox jumps over"


def test_quote_not_in_excerpt_rejected():
    r = check_answer(raw("x", "a purple cat sat"), EXCERPT)
    assert not r.ok and r.reason == "quote_not_in_excerpt"


def test_model_cannot_answer_rejected():
    r = check_answer(raw("", ""), EXCERPT)
    assert not r.ok and r.reason == "model_cannot_answer"


def test_bad_json_does_not_crash():
    for bad in ["", "not json", "{broken", "[]", None, "{\"answer\": 5}"]:
        assert not check_answer(bad, EXCERPT).ok


def test_wrong_field_types_rejected():
    r = check_answer(json.dumps({"answer": ["a"], "supporting_quote": 3}), EXCERPT)
    assert not r.ok and r.reason == "wrong_fields"


def test_invented_quote_inside_answer_rejected():
    answer = 'She said "I love fixing every network problem" once.'
    r = check_answer(raw(answer, "brown fox jumps over"), EXCERPT)
    assert not r.ok and r.reason == "invented_quote_in_answer"


def test_real_quote_inside_answer_allowed():
    answer = 'The text says "quick brown fox jumps".'
    assert check_answer(raw(answer, "brown fox jumps over"), EXCERPT).ok


def test_json_with_think_block_and_fence():
    text = "<think>hmm {\"answer\": \"wrong\"}</think>\n```json\n" + raw("ok", "sunny day") + "\n```"
    assert parse_model_json(text)["answer"] == "ok"


def test_json_with_text_around_it():
    text = "Sure! " + raw("ok", "sunny day") + " Hope that helps."
    assert parse_model_json(text)["answer"] == "ok"
