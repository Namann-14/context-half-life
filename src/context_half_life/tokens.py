"""One fixed reference tokenizer, so "input tokens" mean the same thing in every condition."""
from functools import lru_cache


@lru_cache(maxsize=1)
def _enc():
    import tiktoken
    return tiktoken.get_encoding("cl100k_base")


def count(text: str) -> int:
    return len(_enc().encode(text, disallowed_special=()))


def count_messages(messages) -> int:
    return sum(count(m["content"]) + 4 for m in messages)
