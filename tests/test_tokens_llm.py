import pytest

from context_half_life import llm, scoring, tokens


def test_token_count_monotone():
    assert tokens.count("hello world") < tokens.count("hello world " * 10)


def test_prompt_hash_stable():
    m = [{"role": "user", "content": "x"}]
    assert llm.prompt_hash(m) == llm.prompt_hash(list(m))


def test_hosted_key_requires_env(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        llm.hosted_key("ANTHROPIC_API_KEY")


def test_scoring():
    assert scoring.contains_answer("It is Blue Tin Box!", "blue tin box")
    assert scoring.is_abstention("I do not know that")
    assert scoring.parse_yes("Yes.")
